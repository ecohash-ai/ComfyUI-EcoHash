export const isDedicated = (type) => type.startsWith("EcoHashDedicated");

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
    };
    if (chinese && special[value]) return special[value];
    const separator = value.indexOf(" / ");
    if (separator < 0 || !/[\u3400-\u9fff]/u.test(value.slice(separator + 3))) return value;
    const translated = chinese ? value.slice(separator + 3) : value.slice(0, separator);
    return chinese && value.startsWith("EcoHash ") ? `EcoHash ${translated}` : translated;
}

export function modelsForNode(models, type) {
    const category = {
        EcoHashLLM: ["llm", "llm_vision"], EcoHashVLMDescribe: ["llm_vision"],
        EcoHashTTS: ["speech_tts"], EcoHashSTT: ["speech_stt"],
    }[type] ?? ["image"];
    return models.filter((model) => {
        if (model.category && !category.includes(model.category)) return false;
        if (type.endsWith("ImageEdit") && model.supports_image_edit === false) return false;
        return true;
    });
}

export function capabilityHint(model, type, locale = "en") {
    const t = (value) => localizedText(value, locale);
    if (!model) return t("Enter an exact model ID, or refresh models to discover available IDs. / 请填写准确的模型 ID，或刷新模型列表。");
    const hints = [model.name || model.id];
    if (type.includes("Image")) {
        if (model.default_image_steps) hints.push(`${t("Default steps / 默认步数")}: ${model.default_image_steps} (steps = 0)`);
        if (typeof model.supports_image_edit === "boolean") hints.push(t(model.supports_image_edit ? "Supports image editing / 支持图像编辑" : "Generation only / 仅图像生成"));
        if (model.supported_sizes?.length) hints.push(`${t("Sizes / 尺寸")}: ${model.supported_sizes.join(", ")}`);
    }
    if (type === "EcoHashTTS") hints.push(model.voices?.length ? `${t("Voices / 音色")}: ${model.voices.join(", ")}` : t("Voice IDs vary by model; enter a voice supported by this model. / 请填写该模型支持的音色 ID。"));
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
