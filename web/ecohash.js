import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { capabilityHint, connectionHint, connectionOptions, isDedicated, localizedText, modelsForNode, replaceOptions, setWidgetVisible } from "./helpers.mjs?v=connections-5";

const state = { connections: [], models: new Map(), requests: new Map(), versions: new Map(), checked: new Map() };
let profilesRequest;
const widget = (node, name) => node.widgets?.find((item) => item.name === name);
const nodeType = (node) => node.comfyClass || node.type;
const connectionId = (node) => isDedicated(nodeType(node)) ? widget(node, "connection")?.value || "dedicated" : "public";
function uiLocale() {
    let locale = navigator.language;
    // Extensions are imported before some frontend versions initialize their
    // extension manager. Registration must also work during that early phase.
    try { locale = app.extensionManager?.setting?.get?.("Comfy.Locale") || locale; }
    catch { /* Use the browser language until ComfyUI finishes initializing. */ }
    return locale;
}
const uiText = (text) => localizedText(text, uiLocale());
const manualModel = uiText("Enter model ID manually / 手动填写模型 ID");
const manualVoice = uiText("Enter voice ID manually / 手动填写音色 ID");

function element(tag, text, className) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = uiText(text);
    if (className) item.className = className;
    return item;
}

async function request(path, method = "GET", body) {
    const response = await api.fetchApi(`/ecohash${path}`, {
        method, headers: method === "GET" ? {} : { "Content-Type": "application/json", "X-EcoHash-Settings": "1" },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}). Check the server log and refresh ComfyUI after updating the plugin.`);
    return result;
}

async function loadProfiles() {
    profilesRequest ??= request("/connections").then((profiles) => {
        state.connections = profiles;
        return profiles;
    }).finally(() => { profilesRequest = null; });
    return profilesRequest;
}

async function loadModels(id, refresh = false) {
    if (!refresh && state.models.has(id)) return state.models.get(id);
    if (!refresh && state.requests.has(id)) return state.requests.get(id);
    const version = (state.versions.get(id) || 0) + 1;
    state.versions.set(id, version);
    const pending = request(`/models/${encodeURIComponent(id)}${refresh ? "?refresh=1" : ""}`).then((result) => {
        if (state.versions.get(id) === version) state.models.set(id, result);
        return result;
    }).finally(() => { if (state.requests.get(id) === pending) state.requests.delete(id); });
    state.requests.set(id, pending);
    return pending;
}

function invalidateModels(id) {
    state.models.delete(id);
    state.requests.delete(id);
    state.versions.set(id, (state.versions.get(id) || 0) + 1);
    state.checked.delete(id);
}

function updateNode(node) {
    const type = nodeType(node);
    const connection = widget(node, "connection");
    if (connection) connection.options.values = replaceOptions(connection.options.values, connectionOptions(state.connections, connection.value));
    const id = connectionId(node);
    const model = widget(node, "model");
    const result = state.models.get(id);
    const models = modelsForNode(result?.models || [], type);
    if (model && !isDedicated(type) && result) {
        // Preserve current selections when catalogs change; never silently choose another model.
        model.options.values = replaceOptions(model.options.values, [...new Set([...models.map((item) => item.id), model.value].filter(Boolean))]);
    }
    const picker = widget(node, "Choose discovered model");
    if (picker) {
        picker.options.values = replaceOptions(picker.options.values, [manualModel, ...models.map((item) => item.id)]);
        picker.value = models.some((item) => item.id === model?.value) ? model.value : manualModel;
    }
    const selected = models.find((item) => item.id === model?.value);
    const voicePicker = widget(node, "Choose voice");
    if (voicePicker) {
        voicePicker.options.values = replaceOptions(voicePicker.options.values, [manualVoice, ...(selected?.voices || [])]);
        const voice = widget(node, "voice")?.value;
        voicePicker.value = selected?.voices?.includes(voice) ? voice : manualVoice;
    }
    const info = widget(node, "Model information");
    if (info) info.value = capabilityHint(selected, type, uiLocale());
    const status = widget(node, "Connection status");
    if (status) status.value = uiText(result?.error || state.checked.get(id)?.message || connectionHint(state.connections, id, uiLocale()));
    for (const name of ["width", "height"]) setVisible(node, name, widget(node, "size")?.value === "custom");
    setVisible(node, "system_prompt", widget(node, "mode")?.value === "custom");
    node.setDirtyCanvas?.(true, true);
}

function setVisible(node, name, visible) {
    setWidgetVisible(widget(node, name), visible);
}

function allNodes() {
    return app.graph?._nodes?.filter((node) => nodeType(node)?.startsWith("EcoHash")) || [];
}

async function refreshNodes() {
    await loadProfiles();
    for (const node of allNodes()) updateNode(node);
}

function field(form, label, name, type = "text") {
    const wrapper = element("label", label);
    const input = element("input");
    input.name = name;
    input.type = type;
    if (type === "password") input.autocomplete = "new-password";
    wrapper.append(input);
    form.append(wrapper);
    return input;
}

function mountManager(root, initialId = "public", close) {
    root.classList.add("ecohash-manager");
    root.replaceChildren();
    if (close) {
        const button = element("button", "Close / 关闭", "eh-close");
        button.onclick = close;
        root.append(button);
    }
    root.append(element("h2", "EcoHash connections / 连接"));
    root.append(element("p", "Configure a connection once, test it, then select its model in your workflow. / 配置连接并测试后，即可在工作流中选择模型。", "eh-muted"));
    const chooser = element("select");
    chooser.setAttribute("aria-label", uiText("Connection / 连接"));
    const toolbar = element("div", undefined, "eh-row");
    const add = element("button", "Add connection / 添加连接");
    toolbar.append(chooser, add);
    root.append(toolbar);
    const form = element("form");
    const id = field(form, "Connection ID / 连接 ID", "connection_id");
    id.pattern = "[A-Za-z0-9][A-Za-z0-9_-]{0,63}";
    id.maxLength = 64;
    id.required = true;
    const name = field(form, "Display name / 显示名称", "name");
    name.required = true;
    name.maxLength = 100;
    const url = field(form, "API base URL / API 前缀地址", "base_url", "url");
    url.placeholder = "https://your-endpoint.example/v1";
    const key = field(form, "API key / 密钥", "api_key", "password");
    const timeout = field(form, "Timeout in seconds / 超时（秒）", "timeout", "number");
    timeout.min = "0.1";
    timeout.step = "any";
    const source = element("p", undefined, "eh-muted");
    form.append(source);
    const actions = element("div", undefined, "eh-row");
    const save = element("button", "Save / 保存", "eh-primary");
    save.type = "submit";
    const test = element("button", "Test connection / 测试连接");
    test.type = "button";
    const discover = element("button", "Refresh models / 刷新模型");
    discover.type = "button";
    const remove = element("button", "Delete saved connection / 删除已保存连接");
    remove.type = "button";
    actions.append(save, test, discover, remove);
    form.append(actions);
    root.append(form);
    const status = element("div", "Loading connections… / 正在读取连接…", "eh-status");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    const models = element("ul", undefined, "eh-models");
    root.append(status, models);
    root.append(element("p", "API keys stay on the ComfyUI server. Blank key fields keep the current key. Environment variables override saved settings, which override config.ini. / 密钥保存在服务端；留空保留原密钥。优先级：环境变量 → 界面设置 → config.ini。", "eh-muted"));
    const detail = element("details");
    detail.append(element("summary", "Generate a test image / 测试出图"));
    const modelInput = field(detail, "Generation model ID / 生成模型 ID", "test_model");
    const confirm = element("label");
    const consent = element("input");
    consent.type = "checkbox";
    confirm.append(consent, document.createTextNode(uiText("This sends a real generation request and may incur charges. / 此操作将实际生成图片，可能产生费用。")));
    const generate = element("button", "Generate test image / 生成测试图片");
    const preview = element("img");
    preview.alt = "EcoHash test generation";
    preview.hidden = true;
    detail.append(confirm, generate, preview);
    root.append(detail);
    const docs = element("a", "Setup guide / 配置说明");
    docs.href = "https://github.com/ecohash-ai/ComfyUI-EcoHash#connection-manager";
    docs.target = "_blank";
    docs.rel = "noopener noreferrer";
    root.append(docs);

    let selectedId = initialId, dirty = false, busy = false, creating = false;
    const message = (text, error = false) => { status.textContent = uiText(text); status.dataset.error = String(error); };
    function controls() {
        save.disabled = busy;
        chooser.disabled = busy;
        add.disabled = busy;
        test.disabled = discover.disabled = busy || dirty || creating;
        remove.disabled = busy || dirty || creating || !state.connections.find((item) => item.id === selectedId)?.can_delete;
        generate.disabled = busy || dirty || creating || !consent.checked || !modelInput.value.trim();
        form.inert = detail.inert = busy;
    }
    form.oninput = () => { dirty = true; message("Unsaved changes. Save before testing. / 配置有修改，请先保存再测试。"); controls(); };
    consent.onchange = modelInput.oninput = controls;
    function select(value, create = false) {
        selectedId = value;
        creating = create;
        dirty = false;
        const profile = state.connections.find((item) => item.id === value);
        if (create && ![...chooser.options].some((option) => option.value === value)) {
            const option = element("option", "New connection / 新连接");
            option.value = value;
            chooser.append(option);
        }
        chooser.value = value;
        id.disabled = !create;
        id.value = create && value === "__new__" ? "" : value;
        name.value = profile?.name || (value === "__new__" ? "" : value);
        url.value = profile?.base_url || "";
        key.value = "";
        timeout.value = profile?.timeout || "300";
        url.disabled = value === "public" || profile?.sources?.base_url === "environment";
        key.disabled = profile?.sources?.api_key === "environment";
        timeout.disabled = value === "public" || profile?.sources?.timeout === "environment";
        key.placeholder = uiText(profile?.has_api_key ? "Configured — leave blank to keep / 已配置，留空保留" : "Enter API key / 输入密钥");
        source.textContent = Object.entries(profile?.sources || {}).filter(([, src]) => src === "environment").map(([field]) => uiText(`${field}: managed by environment / ${field}：由环境变量管理`)).join(" · ");
        models.replaceChildren();
        consent.checked = false;
        modelInput.value = "";
        preview.hidden = true;
        preview.removeAttribute("src");
        message(create ? "Enter a stable connection ID. Shared workflows refer to this ID. / 工作流通过连接 ID 引用配置。" : profile?.message || "Connection is missing. Add it with this ID, or choose another connection in the workflow. / 缺少连接，请创建同名连接或在节点中重新选择。");
        controls();
    }
    async function reload(preferred = selectedId) {
        await loadProfiles();
        chooser.replaceChildren(...state.connections.map((item) => {
            const option = element("option", `${item.name} (${item.id})`);
            option.value = item.id;
            return option;
        }));
        const missing = !state.connections.some((item) => item.id === preferred);
        if (missing) {
            const option = element("option", `Missing connection / 缺少连接: ${preferred}`);
            option.value = preferred;
            chooser.append(option);
        }
        chooser.value = preferred;
        select(preferred, missing);
    }
    async function operation(label, fn) {
        busy = true;
        controls();
        message(label);
        try { await fn(); }
        catch (error) { message(error.message, true); }
        finally { busy = false; controls(); }
    }
    chooser.onchange = () => select(chooser.value);
    add.onclick = () => select("__new__", true);
    form.onsubmit = (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        if (creating && state.connections.some((item) => item.id === id.value.trim())) {
            message("This connection ID already exists. Select it to edit its settings. / 连接 ID 已存在，请选择对应连接后编辑。", true);
            return;
        }
        operation("Saving… / 正在保存…", async () => {
            const target = id.value.trim();
            const body = { name: name.value, ...(!url.disabled ? { base_url: url.value } : {}), ...(!timeout.disabled ? { timeout: timeout.value } : {}), ...(!key.disabled ? { api_key: key.value } : {}) };
            const saved = await request(`/connections/${encodeURIComponent(target)}`, "PUT", body);
            key.value = "";
            invalidateModels(target);
            await reload(target);
            await refreshNodes();
            message(saved.configured ? "Saved. Test the connection next. / 已保存，请测试连接。" : saved.message);
        });
    };
    test.onclick = () => operation("Connecting… / 正在检测连接…", async () => {
        const result = await request(`/connections/${encodeURIComponent(selectedId)}/test`, "POST", {});
        state.checked.set(selectedId, result);
        for (const node of allNodes()) if (connectionId(node) === selectedId) updateNode(node);
        message(result.message);
    });
    discover.onclick = () => operation("Loading models… / 正在读取模型…", async () => {
        const result = await loadModels(selectedId, true);
        models.replaceChildren(...result.models.map((item) => element("li", `${item.name} — ${item.id}${item.supports_image_edit === true ? ` · ${uiText("image edit / 可编辑")}` : ""}`)));
        message(result.error || `Loaded ${result.models.length} models (${result.source}). / 已读取 ${result.models.length} 个模型。`);
        for (const node of allNodes()) updateNode(node);
    });
    remove.onclick = () => operation("Removing… / 正在删除…", async () => {
        const approved = await app.extensionManager.dialog.confirm({ title: uiText("Remove connection / 删除连接"), message: uiText(`Remove '${selectedId}'? Workflows using this ID will need another connection. / 删除连接 '${selectedId}'？使用此连接的工作流需要重新配置。`), type: "delete" });
        if (!approved) return;
        await request(`/connections/${encodeURIComponent(selectedId)}`, "DELETE");
        invalidateModels(selectedId);
        await reload("public");
        await refreshNodes();
    });
    generate.onclick = () => operation("Generating… please wait for the configured timeout. / 正在生成，请等待服务返回。", async () => {
        const result = await request(`/connections/${encodeURIComponent(selectedId)}/generate-test`, "POST", { model: modelInput.value.trim(), confirm_generation: consent.checked });
        preview.src = `data:image/png;base64,${result.image}`;
        preview.hidden = false;
        consent.checked = false;
        message(`Generation passed: ${result.width} × ${result.height}. / 测试出图成功：${result.width} × ${result.height}。`);
    });
    reload().catch((error) => message(error.message, true));
}

function showManager(id = "public") {
    const existing = document.querySelector("dialog.ecohash-dialog");
    if (existing) { existing.focus(); return; }
    const dialog = element("dialog", undefined, "ecohash-dialog");
    dialog.setAttribute("aria-label", uiText("EcoHash connections / 连接设置"));
    const root = element("div");
    dialog.append(root);
    document.body.append(dialog);
    mountManager(root, id, () => dialog.close());
    dialog.onclose = () => dialog.remove();
    dialog.showModal();
}

function hookWidget(node, name, fn) {
    const item = widget(node, name);
    if (!item) return;
    const previous = item.callback;
    item.callback = function (...args) { previous?.apply(this, args); fn(...args); };
}

app.registerExtension({
    name: "EcoHash.Connections",
    commands: [{ id: "EcoHash.ManageConnections", label: uiText("EcoHash connections / 连接设置"), function: () => showManager() }],
    menuCommands: [{ path: ["Extensions", "EcoHash"], commands: ["EcoHash.ManageConnections"] }],
    setup() {
        const style = element("link");
        style.rel = "stylesheet";
        style.href = new URL("./ecohash.css", import.meta.url).href;
        document.head.append(style);
        app.extensionManager.registerSidebarTab({ id: "ecohash-connections", icon: "pi pi-cloud", title: "EcoHash", tooltip: uiText("EcoHash connections / 连接设置"), type: "custom", render: (root) => mountManager(root) });
        loadProfiles().then(() => Promise.all([...new Set(allNodes().map(connectionId))].map((id) => loadModels(id).catch(() => null))))
            .then(() => allNodes().forEach(updateNode)).catch(() => {});
        let activeNode;
        function executionStatus(node, message) {
            const status = widget(node, "Connection status");
            if (status) status.value = uiText(message);
            node.setDirtyCanvas?.(true, true);
        }
        api.addEventListener("executing", (event) => {
            const id = typeof event.detail === "object" ? event.detail?.node : event.detail;
            const node = id == null ? null : app.graph?.getNodeById(id);
            // Non-output nodes do not emit `executed`. A transition to the next
            // node (or null at the end) is their completion signal.
            if (activeNode && activeNode !== node) executionStatus(activeNode, "Completed / 已完成");
            activeNode = null;
            if (nodeType(node || {})?.startsWith("EcoHash")) {
                activeNode = node;
                executionStatus(node, "Waiting for remote inference… / 正在等待远程推理…");
            }
        });
        for (const eventName of ["executed", "execution_error", "execution_interrupted"]) api.addEventListener(eventName, (event) => {
            const node = app.graph?.getNodeById(event.detail?.node ?? event.detail?.node_id) || activeNode;
            if (!nodeType(node || {})?.startsWith("EcoHash")) return;
            if (node === activeNode) activeNode = null;
            executionStatus(node, eventName === "executed" ? "Completed / 已完成" : eventName === "execution_interrupted" ? "Interrupted / 已中断" : "Request failed. Open Connections or check the execution error. / 请求失败，请检查连接和运行错误。");
        });
        api.addEventListener("execution_cached", (event) => {
            for (const id of event.detail?.nodes || []) {
                const node = app.graph?.getNodeById(id);
                if (nodeType(node || {})?.startsWith("EcoHash")) executionStatus(node, "Cached result / 使用缓存结果");
            }
        });
    },
    nodeCreated(node) {
        const type = nodeType(node);
        if (!type?.startsWith("EcoHash")) return;
        node.addWidget("button", "Connections / 连接设置", null, () => showManager(connectionId(node)), { serialize: false });
        if (isDedicated(type)) node.addWidget("combo", "Choose discovered model", manualModel, (value) => {
            if (value === manualModel) return;
            const model = widget(node, "model");
            model.value = value;
            model.callback?.(value);
            updateNode(node);
        }, { values: [manualModel], serialize: false });
        if (type === "EcoHashTTS") node.addWidget("combo", "Choose voice", manualVoice, (value) => {
            if (value !== manualVoice) widget(node, "voice").value = value;
        }, { values: [manualVoice], serialize: false });
        node.addWidget("button", "Refresh models / 刷新模型", null, async () => {
            const status = widget(node, "Connection status");
            if (status) status.value = uiText("Loading models… / 正在读取模型…");
            try {
                await loadProfiles();
                const result = await loadModels(connectionId(node), true);
                updateNode(node);
                if (status) status.value = uiText(result.error || `Models refreshed (${result.source}) / 模型已刷新`);
            } catch (error) { if (status) status.value = error.message; }
            node.setDirtyCanvas?.(true, true);
        }, { serialize: false });
        for (const name of ["Connection status", "Model information"]) {
            const item = node.addWidget("text", name, "", () => {}, { serialize: false });
            item.options.read_only = true;
        }
        const labels = { "Choose discovered model": "选择已发现的模型", "Choose voice": "选择音色", "Connection status": "连接状态", "Model information": "模型信息" };
        for (const item of node.widgets || []) {
            if (item.options?.serialize === false) item.label = uiText(labels[item.name] ? `${item.name} / ${labels[item.name]}` : item.name);
        }
        hookWidget(node, "connection", async () => {
            updateNode(node);
            widget(node, "Connection status").value = uiText("Loading models… / 正在读取模型…");
            try { await loadModels(connectionId(node)); updateNode(node); }
            catch (error) { widget(node, "Connection status").value = error.message; }
        });
        hookWidget(node, "model", () => {
            if (type === "EcoHashTTS") {
                const selected = state.models.get("public")?.models?.find((item) => item.id === widget(node, "model")?.value);
                if (selected?.voices?.length) widget(node, "voice").value = selected.voices[0];
                else if (widget(node, "model").value !== "kokoro-82m" && widget(node, "voice").value === "af_bella") widget(node, "voice").value = "";
            }
            updateNode(node);
        });
        for (const name of ["mode", "size"]) hookWidget(node, name, () => updateNode(node));
        const configured = node.onConfigure;
        node.onConfigure = function (...args) { configured?.apply(this, args); updateNode(this); };
        updateNode(node);
        loadProfiles().then(() => loadModels(connectionId(node))).then(() => updateNode(node)).catch((error) => {
            const status = widget(node, "Connection status");
            if (status) status.value = error.message;
        });
    },
});
