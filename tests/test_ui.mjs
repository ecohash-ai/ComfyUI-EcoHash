import assert from "node:assert/strict";
import test from "node:test";
import { modelsForNode, capabilityHint, connectionHint, connectionOptions, defaultConnection, isEcoHashUrl, localizedText, migrateVideoWorkflow, replaceOptions, setWidgetVisible, singleModel } from "../web/helpers.mjs";

test("only the exact EcoHash HTTPS origin uses the global key", () => {
    for (const url of ["https://api.ecohash.com/v1", "https://API.ECOHASH.COM:443/inference-instances/999/proxy/v1/videos/"]) assert.equal(isEcoHashUrl(url), true);
    for (const url of ["http://api.ecohash.com/v1", "https://api.ecohash.com:8443/v1", "https://api.ecohash.com.evil.example/v1",
        "https://custom.ecohash.com/v1", "https://evil.example/api.ecohash.com/v1", "https://user@api.ecohash.com/v1",
        "https://api.ecohash.com/v1?target=elsewhere", "https://api.ecohash.com/v1#fragment", "https://api.ecohash.com/bad path", "", null]) assert.equal(isEcoHashUrl(url), false, String(url));
});

test("conditional widgets recover their original type, visibility and undefined sizing", () => {
    const item = { type: "number", hidden: false };
    setWidgetVisible(item, false);
    setWidgetVisible(item, false);
    setWidgetVisible(item, true);
    assert.equal(item.type, "number");
    assert.equal(item.hidden, false);
    assert.equal(item.computeSize, undefined);
});

test("conditional visibility works with ComfyUI's hidden-type compatibility shim", () => {
    let type = "number", hidden = false, rawHidden = false;
    const item = {
        get type() { return type; },
        set type(value) { const wasHidden = type === "hidden"; type = value; if (value === "hidden") hidden = true; else if (wasHidden) hidden = rawHidden; },
        get hidden() { return hidden; },
        set hidden(value) { hidden = value; if (type !== "hidden") rawHidden = value; },
    };
    setWidgetVisible(item, false);
    setWidgetVisible(item, true);
    assert.equal(item.hidden, false);
});

test("dynamic options retain the array shared with the Vue property inspector", () => {
    const original = ["manual"];
    assert.equal(replaceOptions(original, ["manual", "private-model"]), original);
    assert.deepEqual(original, ["manual", "private-model"]);
    assert.deepEqual(replaceOptions(Object.freeze(["old"]), ["new"]), ["new"]);
});

test("UI labels follow ComfyUI language without duplicate bilingual paragraphs", () => {
    assert.equal(localizedText("Test connection / 测试连接", "zh"), "测试连接");
    assert.equal(localizedText("Test connection / 测试连接", "en"), "Test connection");
    assert.equal(localizedText("EcoHash connections / 连接设置", "zh-CN"), "EcoHash 连接设置");
    assert.equal(localizedText("EcoHash API Key verified. / EcoHash API Key 验证通过。", "zh-CN"), "EcoHash API Key 验证通过。");
    assert.equal(localizedText("https://example.com/v1", "zh"), "https://example.com/v1");
    assert.equal(localizedText("Set ENV / [dedicated] base_url", "zh"), "Set ENV / [dedicated] base_url");
});

test("discovery filters capabilities while retaining unknown private models", () => {
    const models = [
        { id: "generate-only", category: "image", supports_image_edit: false },
        { id: "editor", category: "image", supports_image_edit: true },
        { id: "unknown-private" }, { id: "tts", category: "speech_tts" },
    ];
    assert.deepEqual(modelsForNode(models, "EcoHashDedicatedImageEdit").map((m) => m.id), ["editor", "unknown-private"]);
    assert.deepEqual(modelsForNode(models, "EcoHashTTS").map((m) => m.id), ["unknown-private", "tts"]);
});

test("missing workflow aliases remain available for explicit remapping", () => {
    const profiles = [{ id: "public" }, { id: "dedicated", configured: false }, { id: "studio", configured: true, name: "Studio" }];
    assert.deepEqual(connectionOptions(profiles, "missing"), ["dedicated", "studio", "missing"]);
    assert.match(connectionHint(profiles, "missing"), /missing/);
    assert.match(connectionHint(profiles, "studio"), /not yet tested/);
});

test("dedicated language nodes discover language models and preserve unknown private IDs", () => {
    const models = [
        { id: "image", category: "image" },
        { id: "text", category: "llm", input_modalities: ["text"] },
        { id: "vision", category: "llm_vision", input_modalities: ["text", "image"] },
        { id: "mislabelled-vision", category: "llm_vision", input_modalities: ["text"] },
        { id: "unknown" },
    ];
    assert.deepEqual(modelsForNode(models, "EcoHashDedicatedLLM").map((m) => m.id), ["text", "vision", "mislabelled-vision", "unknown"]);
    assert.deepEqual(modelsForNode(models, "EcoHashDedicatedVLMDescribe").map((m) => m.id), ["vision", "unknown"]);
    assert.match(capabilityHint(models[2], "EcoHashDedicatedVLMDescribe", "zh"), /支持图片输入.*text, image/);
    const audio = [{ id: "tts", category: "speech_tts", voices: ["speaker-a"] }, { id: "stt", category: "speech_stt" }];
    assert.deepEqual(modelsForNode(audio, "EcoHashDedicatedTTS").map((m) => m.id), ["tts"]);
    assert.deepEqual(modelsForNode(audio, "EcoHashDedicatedSTT").map((m) => m.id), ["stt"]);
    assert.match(capabilityHint(audio[0], "EcoHashDedicatedTTS", "zh"), /音色: speaker-a/);
});

test("hints expose known capabilities and never invent private model support", () => {
    assert.match(capabilityHint({ id: "m", default_image_steps: 8, supports_image_edit: false }, "EcoHashImageGenerate"), /Default steps: 8/);
    assert.match(capabilityHint({ id: "m" }, "EcoHashTTS"), /Voice IDs vary/);
    assert.match(capabilityHint({ id: "m", voices: ["speaker-a"] }, "EcoHashTTS"), /speaker-a/);
    assert.match(capabilityHint({ id: "m", default_image_steps: 8, supports_image_edit: false }, "EcoHashImageGenerate", "zh"), /默认步数: 8.*仅图像生成/);
});

test("video nodes discover video models without mixing image or language categories", () => {
    const models = [{ id: "v", category: "video" }, { id: "i", category: "image" }, { id: "unknown" }];
    assert.deepEqual(modelsForNode(models, "EcoHashDedicatedVideoGenerate").map((m) => m.id), ["v", "unknown"]);
    assert.deepEqual(modelsForNode(models, "EcoHashVideoGenerate").map((m) => m.id), ["v", "unknown"]);
    assert.match(capabilityHint(models[0], "EcoHashDedicatedVideoGenerate", "zh"), /文生视频.*保存视频/);
});

test("vision uses server-declared image input even when the model category is llm", () => {
    const models = [
        { id: "new-multimodal-model", category: "llm", input_modalities: ["text", "image"] },
        { id: "text-only", category: "llm", input_modalities: ["text"] },
        { id: "unspecified", category: "llm" },
    ];
    assert.deepEqual(modelsForNode(models, "EcoHashVLMDescribe").map((m) => m.id), ["new-multimodal-model"]);
});

test("model names do not determine capabilities; server categories and modalities do", () => {
    const names = ["seedance-next", "MiniMaxAI/MiniMax-H3:247", "wan3-next", "ltx-next"];
    const models = names.map((id) => ({ id }));
    assert.deepEqual(modelsForNode(models, "EcoHashDedicatedImageGenerate"), models);
    assert.deepEqual(modelsForNode(models, "EcoHashDedicatedVideoGenerate"), models);
    assert.match(capabilityHint(models[0], "EcoHashDedicatedVideoGenerate", "zh"), /能力信息.*尚未验证/);
    const declared = [
        { id: "renamed", input_modalities: ["text"], output_modalities: ["video"] },
        { id: "another", input_modalities: ["image"], output_modalities: ["text"] },
        { id: "custom", openai_compatible: false },
        { id: "embed", category: "embedding", input_modalities: ["text"], output_modalities: ["text"] },
        { id: "rank", category: "reranker", input_modalities: ["text"], output_modalities: ["text"] },
        { id: "music", category: "audio_music", input_modalities: ["text"], output_modalities: ["audio"] },
    ];
    assert.deepEqual(modelsForNode(declared, "EcoHashDedicatedVideoGenerate").map((m) => m.id), ["renamed"]);
    assert.deepEqual(modelsForNode(declared, "EcoHashDedicatedVLMDescribe").map((m) => m.id), ["another"]);
    assert.deepEqual(modelsForNode(declared, "EcoHashDedicatedLLM"), []);
    assert.deepEqual(modelsForNode(declared, "EcoHashDedicatedTTS"), []);
});

test("new nodes only default to an unambiguous or deliberately preferred connection", () => {
    const profiles = [{ id: "public", configured: true }, { id: "dedicated", configured: false }, { id: "one", configured: true }];
    assert.equal(defaultConnection(profiles), "one");
    profiles.push({ id: "two", configured: true });
    assert.equal(defaultConnection(profiles), null);
    assert.equal(defaultConnection(profiles, "two"), "two");
    assert.equal(defaultConnection(profiles, "dedicated"), null);
    assert.equal(singleModel([{ id: "one" }], ""), "one");
    assert.equal(singleModel([{ id: "new" }], "old"), "old");
    assert.equal(singleModel([{ id: "one" }, { id: "two" }], ""), "");
});

function oldVideoWorkflow(dedicated, named, objectLinks = false) {
    const names = ["model", "prompt", ...(dedicated ? ["protocol"] : []), "duration", "aspect_ratio", "resolution", "generate_audio", "width", "height", "steps", "seed", "control_after_generate", "job_id", "wait_timeout", ...(dedicated ? ["connection"] : [])];
    const values = { model: "custom/model", prompt: "cat", protocol: "openai", duration: 8, aspect_ratio: "16:9", resolution: "4k", generate_audio: true, width: 1280, height: 720, steps: 50, seed: 42, control_after_generate: "randomize", job_id: "completed-job", wait_timeout: 900, connection: "studio" };
    const inputs = names.filter((n) => n !== "control_after_generate").map((name) => ({ name }));
    const links = [
        [1, 2, 0, 1, inputs.findIndex((i) => i.name === "steps"), "INT"],
        [2, 2, 1, 1, inputs.findIndex((i) => i.name === "job_id"), "STRING"],
    ];
    return { nodes: [{ id: 1, type: dedicated ? "EcoHashDedicatedVideoGenerate" : "EcoHashVideoGenerate", inputs, widgets_values: names.map((n) => values[n]), ...(named ? { widgets_values_named: values } : {}) }, { id: 2, outputs: [{ links: [1] }, { links: [2] }] }], links: objectLinks ? links.map(([id, origin_id, origin_slot, target_id, target_slot, type]) => ({ id, origin_id, origin_slot, target_id, target_slot, type })) : links };
}

for (const dedicated of [true, false]) for (const named of [true, false]) for (const objectLinks of [true, false]) {
    test(`video workflow migration preserves values and link slots (${dedicated}, ${named}, ${objectLinks})`, () => {
        const graph = oldVideoWorkflow(dedicated, named, objectLinks);
        migrateVideoWorkflow(graph);
        const node = graph.nodes[0];
        assert.equal(node.widgets_values.length, dedicated ? 10 : 8);
        assert.equal(node.widgets_values_named.job_id, "completed-job");
        assert.equal(node.widgets_values_named.wait_timeout, 900);
        assert.equal(node.widgets_values_named.protocol, undefined);
        assert.equal(node.widgets_values_named.seed, undefined);
        if (dedicated) {
            assert.equal(node.widgets_values_named.resolution, "custom");
            assert.equal(node.widgets_values_named.width, 1280);
            assert.equal(node.widgets_values_named.connection, "studio");
        }
        assert.equal(graph.links.length, 1);
        const slot = objectLinks ? graph.links[0].target_slot : graph.links[0][4];
        assert.equal(node.inputs[slot].name, "job_id");
        assert.deepEqual(graph.nodes[1].outputs.map((o) => o.links), [[], [2]]);
        const migrated = JSON.stringify(graph);
        migrateVideoWorkflow(graph);
        assert.equal(JSON.stringify(graph), migrated);
    });
}

test("subgraph video workflows migrate and flag retired native contracts", () => {
    const child = oldVideoWorkflow(true, true);
    child.nodes[0].widgets_values_named.protocol = "retired-native";
    const parent = { definitions: { subgraphs: [child] } };
    migrateVideoWorkflow(parent);
    assert.equal(child.nodes[0].properties.ecohash_video_schema, 3);
    assert.equal(child.nodes[0].properties.ecohash_migration_warning, true);
});
