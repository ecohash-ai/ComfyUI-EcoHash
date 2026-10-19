import assert from "node:assert/strict";
import test from "node:test";
import { modelsForNode, capabilityHint, connectionHint, connectionOptions, localizedText, replaceOptions, setWidgetVisible } from "../web/helpers.mjs";

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
