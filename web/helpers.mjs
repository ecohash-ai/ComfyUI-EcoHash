export const isDedicated = (type) => type.startsWith("EcoHashDedicated");

export function defaultConnection(profiles, preferred) {
    const ready = profiles.filter((p) => p.id !== "public" && p.configured);
    if (ready.some((p) => p.id === preferred)) return preferred;
    return ready.length === 1 ? ready[0].id : null;
}

export function singleModel(models, current) {
    return !current && models.length === 1 ? models[0].id : current;
}

export function migrateVideoWorkflow(data) {
    for (const node of data?.nodes || []) {
        if (!["EcoHashVideoGenerate", "EcoHashDedicatedVideoGenerate"].includes(node.type)) continue;
        const dedicated = isDedicated(node.type);
        const oldNames = ["model", "prompt", ...(dedicated ? ["protocol"] : []), "duration", "aspect_ratio", "resolution", "generate_audio", "width", "height", "steps", "seed", "control_after_generate", "job_id", "wait_timeout", ...(dedicated ? ["connection"] : [])];
        const named = node.widgets_values_named;
        if (node.properties?.ecohash_video_schema === 3) continue;
        if (!named && node.widgets_values?.length !== oldNames.length) continue;
        const values = named ? { ...named } : Object.fromEntries(oldNames.map((name, index) => [name, node.widgets_values[index]]));
        if (dedicated && values.protocol === "openai") values.resolution = "custom";
        const removed = new Set(["protocol", "steps", "seed", "control_after_generate", ...(dedicated ? ["generate_audio"] : ["width", "height"])]);
        const names = oldNames.filter((name) => !removed.has(name));
        node.widgets_values = names.map((name) => values[name]);
        node.widgets_values_named = Object.fromEntries(names.map((name) => [name, values[name]]));
        const oldInputs = node.inputs || [];
        node.inputs = oldInputs.filter((input) => !removed.has(input.name));
        const dropped = new Set();
        data.links = data.links?.filter((link) => {
            const target = Array.isArray(link) ? link[3] : link.target_id;
            if (String(target) !== String(node.id)) return true;
            const oldSlot = Array.isArray(link) ? link[4] : link.target_slot;
            const input = oldInputs[oldSlot];
            if (!input) return true;
            const slot = node.inputs.indexOf(input);
            if (slot < 0) { dropped.add(Array.isArray(link) ? link[0] : link.id); return false; }
            if (Array.isArray(link)) link[4] = slot;
            else link.target_slot = slot;
            return true;
        });
        for (const source of data.nodes) for (const output of source.outputs || []) if (output.links) output.links = output.links.filter((id) => !dropped.has(id));
        node.properties ??= {};
        node.properties.ecohash_video_schema = 3;
        if (dedicated && values.protocol && values.protocol !== "openai") node.properties.ecohash_migration_warning = true;
    }
    for (const subgraph of data?.definitions?.subgraphs || []) migrateVideoWorkflow(subgraph);
}

export function setWidgetVisible(item, visible) {
    if (!item) return;
    item._ehVisibleState ??= { type: item.type, computeSize: item.computeSize };
    // Restore the type first: recent ComfyUI versions mirror the hidden type
    // through a visibility shim and otherwise reapply the previous suppression.
    item.type = visible ? item._ehVisibleState.type : "hidden";
    item.hidden = !visible;
    item.computeSize = visible ? item._ehVisibleState.computeSize : () => [0, -4];
}

export function replaceOptions(existing, next) {
    // ComfyUI's Vue inspector can retain the original options array. Keep its
    // identity so both the canvas and inspector see a discovery refresh.
    if (Array.isArray(existing) && !Object.isFrozen(existing)) {
        existing.splice(0, existing.length, ...next);
        return existing;
    }
    return next;
}

export function localizedText(value, locale = "en") {
    if (typeof value !== "string") return value;
    const chinese = locale.toLowerCase().startsWith("zh");
    const special = {
        "Configured; connection has not been tested.": "配置已就绪，尚未测试连接。",
        "Connected and authenticated. No image was generated.": "连接和鉴权已通过，未执行图像生成。",
        "Connected and authenticated. No inference request was sent.": "连接和鉴权已通过，未发送推理请求。",
    };
    if (chinese && special[value]) return special[value];
    const separator = value.indexOf(" / ");
    if (separator < 0 || !/[\u3400-\u9fff]/u.test(value.slice(separator + 3))) return value;
    const translated = chinese ? value.slice(separator + 3) : value.slice(0, separator);
    return chinese && value.startsWith("EcoHash ") ? `EcoHash ${translated}` : translated;
}

export function modelsForNode(models, type) {
    type = type.replace(/^EcoHashDedicated/u, "EcoHash");
    const category = {
        EcoHashLLM: ["llm", "llm_vision"], EcoHashVLMDescribe: ["llm", "llm_vision"],
        EcoHashTTS: ["speech_tts"], EcoHashSTT: ["speech_stt"],
        EcoHashVideoGenerate: ["video"],
    }[type] ?? ["image"];
    const modalities = {
        EcoHashLLM: ["text", "text"], EcoHashVLMDescribe: ["image", "text"],
        EcoHashTTS: ["text", "audio"], EcoHashSTT: ["audio", "text"],
        EcoHashVideoGenerate: ["text", "video"], EcoHashImageGenerate: ["text", "image"],
        EcoHashImageEdit: ["image", "image"],
    }[type];
    return models.filter((model) => {
        if (model.openai_compatible === false) return false;
        // Categories describe API operations; modalities alone cannot distinguish
        // speech from music, or chat from embeddings with the same text I/O.
        // Missing categories can still be filtered using declared modalities.
        if (model.category && !category.includes(model.category)) return false;
        if (type.endsWith("VLMDescribe") && model.category === "llm" && !model.input_modalities?.includes("image")) return false;
        if (modalities && model.input_modalities?.length && !model.input_modalities.includes(modalities[0])) return false;
        if (modalities && model.output_modalities?.length && !model.output_modalities.includes(modalities[1])) return false;
        if (type.endsWith("ImageEdit") && model.supports_image_edit === false) return false;
        return true;
    });
}

export function capabilityHint(model, type, locale = "en") {
    const t = (value) => localizedText(value, locale);
    if (!model) return t("Enter an exact model ID, or refresh models to discover available IDs. / 请填写准确的模型 ID，或刷新模型列表。");
    const hints = [model.name || model.id];
    if (!model.category && !model.input_modalities?.length && !model.output_modalities?.length) hints.push(t("Capabilities not supplied; compatibility is unverified / 服务未提供能力信息，节点兼容性尚未验证"));
    if (type.endsWith("VLMDescribe")) hints.push(t("Requires image-input support / 需要模型支持图片输入"));
    if (type.endsWith("LLM") || type.endsWith("VLMDescribe")) {
        if (model.input_modalities?.length) hints.push(`${t("Inputs / 输入")}: ${model.input_modalities.join(", ")}`);
        if (model.output_modalities?.length) hints.push(`${t("Outputs / 输出")}: ${model.output_modalities.join(", ")}`);
    }
    if (type.includes("Image")) {
        if (model.default_image_steps) hints.push(`${t("Default steps / 默认步数")}: ${model.default_image_steps} (steps = 0)`);
        if (typeof model.supports_image_edit === "boolean") hints.push(t(model.supports_image_edit ? "Supports image editing / 支持图像编辑" : "Generation only / 仅图像生成"));
        if (model.supported_sizes?.length) hints.push(`${t("Sizes / 尺寸")}: ${model.supported_sizes.join(", ")}`);
    }
    if (type.endsWith("TTS")) hints.push(model.voices?.length ? `${t("Voices / 音色")}: ${model.voices.join(", ")}` : t("Voice IDs vary by model; enter a voice supported by this model. / 请填写该模型支持的音色 ID。"));
    if (type.endsWith("VideoGenerate")) {
        hints.push(t("Text-to-video; asynchronous job → MP4 with audio when supported → Save Video / 文生视频：异步任务 → MP4（保留音轨）→ 保存视频"));
        if (model.video_min_duration_seconds) hints.push(`${t("Minimum seconds / 最短秒数")}: ${model.video_min_duration_seconds}`);
        if (model.video_max_duration_seconds) hints.push(`${t("Maximum seconds / 最长秒数")}: ${model.video_max_duration_seconds}`);
        hints.push(model.supported_resolutions?.length ? `${t("Resolutions / 分辨率")}: ${model.supported_resolutions.join(", ")}` : t("Size presets do not establish model support / 通用尺寸预设不代表该模型支持"));
    }
    return hints.join(" · ");
}

export function connectionOptions(profiles, current) {
    const ids = profiles.filter((profile) => profile.id !== "public").map((profile) => profile.id);
    if (current && !ids.includes(current)) ids.push(current); // Preserve a missing workflow alias for explicit remapping.
    return ids.length ? ids : ["dedicated"];
}

export function connectionHint(profiles, id, locale = "en") {
    const connection = profiles.find((profile) => profile.id === id);
    if (!connection) return localizedText(`Connection '${id}' is missing. Open Connections to create it, or select another connection. / 缺少连接 '${id}'，请在连接设置中创建或重新选择连接。`, locale);
    return connection.configured ? `${connection.name} · ${localizedText("configured (not yet tested) / 已配置，尚未测试", locale)}` : localizedText(connection.message, locale);
}
