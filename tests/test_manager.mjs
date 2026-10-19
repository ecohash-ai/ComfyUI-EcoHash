import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import test from "node:test";
import vm from "node:vm";
import * as helpers from "../web/helpers.mjs";

// Exercise the real manager handlers with a small DOM and HTTP harness. No
// browser, credentials, external service, or generation request is needed.
class Element {
    constructor(tag) {
        this.tagName = tag;
        this.children = [];
        this.classList = { add() {} };
        this.value = "";
        this.disabled = this.inert = this.hidden = false;
        this.dataset = {};
    }
    append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
    replaceChildren(...children) { this.children = []; this.append(...children); }
    setAttribute(name, value) { this[name] = value; }
    removeAttribute(name) { delete this[name]; }
    get options() { return this.children; }
    reportValidity() { return true; }
    click() {
        for (let item = this; item; item = item.parentElement) if (item.disabled || item.inert) return;
        this.onclick?.();
    }
    submit() {
        if (!this.inert) this.onsubmit?.({ preventDefault() {} });
    }
}

function descendants(root) { return [root, ...root.children.flatMap(descendants)]; }
function find(root, predicate) {
    const matches = descendants(root).filter(predicate);
    assert.equal(matches.length, 1);
    return matches[0];
}
async function settle() { for (let i = 0; i < 12; i++) await new Promise(setImmediate); }

async function manager() {
    let releaseProfiles;
    const initialProfiles = new Promise((resolve) => { releaseProfiles = resolve; });
    let first = true;
    const profiles = new Map([["public", { id: "public", name: "EcoHash public API", configured: true, has_api_key: true, uses_global_key: true, sources: {} }]]);
    const puts = [];
    const context = vm.createContext({
        ...helpers,
        navigator: { language: "en" },
        crypto: { randomUUID },
        document: { createElement: (tag) => new Element(tag), createTextNode: (text) => Object.assign(new Element("#text"), { textContent: text }) },
        app: { registerExtension() {}, graph: { _nodes: [] }, canvas: { selected_nodes: {} } },
        api: { async fetchApi(path, options) {
            let value;
            if (path === "/ecohash/connections") {
                if (first) { first = false; await initialProfiles; }
                value = [...profiles.values()];
            } else if (options.method === "PUT") {
                const id = path.split("/").at(-1);
                const body = JSON.parse(options.body);
                puts.push({ id, ...body });
                value = { id, ...body, configured: true, has_api_key: true, uses_global_key: true, can_delete: true, sources: {} };
                profiles.set(id, value);
            } else if (path.startsWith("/ecohash/models/")) {
                value = { models: [{ id: "served-model" }], discovery_supported: true, source: "live" };
            } else throw new Error(`Unexpected request: ${path}`);
            return { ok: true, async json() { return value; } };
        } },
    });
    const source = (await readFile(new URL("../web/ecohash.js", import.meta.url), "utf8"))
        .replace(/^import .*;\n/gmu, "").replaceAll("import.meta.url", '"https://local.invalid/ecohash.js"');
    vm.runInContext(source, context);
    const root = new Element("root");
    context.root = root;
    vm.runInContext("mountManager(root)", context);
    return { root, profiles, puts, releaseProfiles };
}

test("initial profile loading blocks editing and adding until the response completes", async () => {
    const { root, releaseProfiles } = await manager();
    const add = find(root, (item) => item.textContent === "Add connection");
    const name = find(root, (item) => item.name === "name");
    assert.equal(add.disabled, true);
    assert.equal(name.parentElement.parentElement.inert, true);
    add.click();
    assert.equal(descendants(root).filter((item) => item.textContent === "New connection").length, 0);
    releaseProfiles();
    await settle();
    assert.equal(add.disabled, false);
    assert.equal(name.parentElement.parentElement.inert, false);
    add.click();
    assert.equal(descendants(root).filter((item) => item.textContent === "New connection").length, 1);
});

test("successive new connections receive distinct IDs and renaming keeps the selected ID", async () => {
    const { root, releaseProfiles, profiles, puts } = await manager();
    releaseProfiles();
    await settle();
    const add = find(root, (item) => item.textContent === "Add connection");
    const name = find(root, (item) => item.name === "name");
    const url = find(root, (item) => item.name === "base_url");
    const form = name.parentElement.parentElement;
    for (const label of ["First deployment", "Second deployment"]) {
        add.click();
        assert.equal(name.value, "");
        name.value = label;
        url.value = "https://api.ecohash.com/v1";
        form.oninput();
        form.submit();
        await settle();
    }
    assert.equal(profiles.size, 3);
    assert.notEqual(puts[0].id, puts[1].id);
    assert.equal(profiles.get(puts[0].id).name, "First deployment");
    name.value = "Renamed deployment";
    form.oninput();
    form.submit();
    await settle();
    assert.equal(profiles.size, 3);
    assert.equal(puts[2].id, puts[1].id);
    assert.equal(profiles.get(puts[1].id).name, "Renamed deployment");
    assert.ok(puts.every((item) => !("api_key" in item)));
});
