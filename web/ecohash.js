import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { capabilityHint, connectionOptions, defaultConnection, isDedicated, isEcoHashUrl, localizedText, migrateVideoWorkflow, modelsForNode, replaceOptions, setWidgetVisible, singleModel } from "./helpers.mjs?v=connections-15";

const state = { connections: [], models: new Map(), requests: new Map(), versions: new Map(), checked: new Map(), preferred: null };
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
const chooseModel = uiText("Select a model / 请选择模型");
const chooseConnection = uiText("Select a connection / 请选择连接");
const connectionLabel = (profile) => `${profile.name} (${profile.id})`;

function modelError(node, error) {
    node._ehDiscoveryError = error.message;
    const status = widget(node, "Execution status");
    if (status) status.value = uiText(error.message);
    node.setDirtyCanvas?.(true, true);
}

function clearModelError(node) {
    const status = widget(node, "Execution status");
    if (node._ehDiscoveryError && status?.value === uiText(node._ehDiscoveryError)) status.value = "";
    delete node._ehDiscoveryError;
}

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
        if (state.versions.get(id) === version) {
            state.models.set(id, result);
            for (const node of allNodes()) if (connectionId(node) === id) {
                if (result.error) modelError(node, new Error(result.error));
                else clearModelError(node);
            }
            if (id !== "public" && result.discovery_supported) state.checked.set(id, { message: "Connected and authenticated. No inference request was sent." });
        }
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
    const connectionPicker = widget(node, "Select connection");
    if (connectionPicker) {
        const ready = state.connections.filter((p) => p.id !== "public" && p.configured);
        const current = state.connections.find((p) => p.id === id);
        connectionPicker.options.values = replaceOptions(connectionPicker.options.values, [...(current?.configured ? [] : [chooseConnection]), ...ready.map(connectionLabel)]);
        connectionPicker.value = current?.configured ? connectionLabel(current) : chooseConnection;
        setVisible(node, "connection", false);
    }
    const model = widget(node, "model");
    const result = state.models.get(id);
    const models = modelsForNode(result?.models || [], type);
    if (isDedicated(type) && model && result && !node._ehManualModel) model.value = singleModel(models, model.value);
    if (model && !isDedicated(type) && result) {
        // Preserve current selections when catalogs change; never silently choose another model.
        model.options.values = replaceOptions(model.options.values, [...new Set([...models.map((item) => item.id), model.value].filter(Boolean))]);
    }
    const picker = widget(node, "Choose discovered model");
    if (picker) {
        picker.options.values = replaceOptions(picker.options.values, [chooseModel, ...models.map((item) => item.id), manualModel]);
        picker.value = node._ehManualModel ? manualModel : models.some((item) => item.id === model?.value) ? model.value : (model?.value ? manualModel : chooseModel);
        setVisible(node, "model", node._ehManualModel || !!model?.value && !models.some((item) => item.id === model.value) || !!result && !models.length);
    }
    const selected = models.find((item) => item.id === model?.value);
    const voicePicker = widget(node, "Choose voice");
    if (voicePicker) {
        if (!widget(node, "voice")?.value && !node._ehManualVoice && selected?.voices?.length) widget(node, "voice").value = selected.voices[0];
        voicePicker.options.values = replaceOptions(voicePicker.options.values, [manualVoice, ...(selected?.voices || [])]);
        const voice = widget(node, "voice")?.value;
        voicePicker.value = selected?.voices?.includes(voice) ? voice : manualVoice;
        setVisible(node, "voice", node._ehManualVoice || !selected?.voices?.includes(voice));
    }
    for (const item of [model, picker]) if (item) item.options.tooltip = capabilityHint(selected, type, uiLocale());
    const isVideo = type.endsWith("VideoGenerate");
    for (const name of ["width", "height"]) setVisible(node, name, widget(node, isVideo ? "resolution" : "size")?.value === "custom");
    if (isVideo) {
        for (const name of ["job_id", "wait_timeout"]) setVisible(node, name, !!node._ehAdvanced || name === "job_id" && !!widget(node, name)?.value);
        setVisible(node, "aspect_ratio", widget(node, "resolution")?.value !== "custom");
        const duration = widget(node, "duration");
        if (duration) {
            duration.options.min = selected?.video_min_duration_seconds || 1;
            duration.options.max = selected?.video_max_duration_seconds || 86400;
        }
        const resolution = widget(node, "resolution");
        if (resolution) resolution._ehDefaultValues ??= [...resolution.options.values];
        if (resolution && selected?.supported_resolutions?.length) resolution.options.values = replaceOptions(resolution.options.values,
            [...new Set([...selected.supported_resolutions, resolution.value])]);
        else if (resolution) resolution.options.values = replaceOptions(resolution.options.values,
            [...new Set([...resolution._ehDefaultValues, resolution.value])]);
    }
    setVisible(node, "system_prompt", widget(node, "mode")?.value === "custom");
    node.setDirtyCanvas?.(true, true);
}

function setVisible(node, name, visible) {
    setWidgetVisible(widget(node, name), visible);
}

function allNodes() {
    return app.graph?._nodes?.filter((node) => nodeType(node)?.startsWith("EcoHash")) || [];
}

async function applyConnection(node, id, resetModel = true) {
    if (!isDedicated(nodeType(node))) return;
    clearModelError(node);
    const connection = widget(node, "connection");
    const changed = connection.value !== id;
    connection.value = id;
    if (changed && resetModel) {
        widget(node, "model").value = "";
        node._ehManualModel = false;
        if (widget(node, "voice")) widget(node, "voice").value = "";
    }
    state.preferred = id;
    updateNode(node);
    await loadModels(id);
    updateNode(node);
}

function selectedDedicatedNode() {
    return Object.values(app.canvas?.selected_nodes || {}).find((node) => isDedicated(nodeType(node) || ""));
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

function mountManager(root, initialId = "public", close, contextNode = selectedDedicatedNode()) {
    root.classList.add("ecohash-manager");
    root.replaceChildren();
    if (close) {
        const button = element("button", "Close / 关闭", "eh-close");
        button.onclick = close;
        root.append(button);
    }
    root.append(element("h2", "EcoHash settings / 设置"));
    root.append(element("p", "Configure your EcoHash API Key once for public models and dedicated EcoHash instances. / 配置一次 EcoHash API Key，公共模型和 EcoHash 专有实例共用。", "eh-muted"));
    const globalForm = element("form");
    const globalKey = field(globalForm, "EcoHash API Key / 全局 API Key", "global_api_key", "password");
    const globalSave = element("button", "Save and verify API Key / 保存并验证 API Key", "eh-primary");
    globalSave.type = "submit";
    const globalStatus = element("p", undefined, "eh-muted");
    globalStatus.setAttribute("role", "status");
    globalStatus.setAttribute("aria-live", "polite");
    globalForm.append(globalSave, globalStatus);
    root.append(globalForm, element("h3", "Model connections / 模型连接"));
    if (contextNode) root.append(element("p", "Saving applies this connection to the current node. / 保存后会将此连接应用到当前节点。", "eh-muted"));
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
    url.placeholder = "https://api.ecohash.com/v1";
    const key = field(form, "Endpoint API key / 端点独立密钥", "api_key", "password");
    const timeout = field(form, "Timeout in seconds / 超时（秒）", "timeout", "number");
    timeout.min = "0.1";
    timeout.step = "any";
    const advanced = element("details");
    advanced.append(element("summary", "Advanced connection settings / 高级连接设置"), id.parentElement, timeout.parentElement, key.parentElement);
    form.append(advanced);
    const source = element("p", undefined, "eh-muted");
    form.append(source);
    const actions = element("div", undefined, "eh-row");
    const save = element("button", "Save and connect / 保存并连接", "eh-primary");
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
    root.append(element("p", "Keys stay on the ComfyUI server. EcoHash HTTPS connections use the global key; other endpoints use their own key in Advanced connection settings. / 密钥保存在 ComfyUI 服务端。EcoHash 官方 HTTPS 连接共用全局 Key，其他端点在高级设置中配置独立密钥。", "eh-muted"));
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
    const textDetail = element("details");
    textDetail.append(element("summary", "Test text inference / 测试文本"));
    const textModel = field(textDetail, "Language model ID / 语言模型 ID", "test_text_model");
    const textConfirm = element("label");
    const textConsent = element("input");
    textConsent.type = "checkbox";
    textConfirm.append(textConsent, document.createTextNode(uiText("This sends a real text inference request and may incur charges. / 此操作将实际调用语言模型，可能产生费用。")));
    const complete = element("button", "Generate test text / 生成测试文本");
    const textPreview = element("pre", undefined, "eh-text-preview");
    textPreview.hidden = true;
    textDetail.append(textConfirm, complete, textPreview);
    root.append(textDetail);
    const docs = element("a", "Setup guide / 配置说明");
    docs.href = "https://github.com/ecohash-ai/ComfyUI-EcoHash#connection-manager";
    docs.target = "_blank";
    docs.rel = "noopener noreferrer";
    root.append(docs);

    let selectedId = initialId, dirty = false, busy = false, creating = false;
    const message = (text, error = false) => { status.textContent = uiText(text); status.dataset.error = String(error); };
    function controls() {
        save.disabled = busy;
        globalSave.disabled = busy;
        chooser.disabled = busy;
        add.disabled = busy;
        test.disabled = discover.disabled = busy || dirty || creating;
        remove.disabled = busy || dirty || creating || !state.connections.find((item) => item.id === selectedId)?.can_delete;
        generate.disabled = busy || dirty || creating || !consent.checked || !modelInput.value.trim();
        complete.disabled = busy || dirty || creating || !textConsent.checked || !textModel.value.trim();
        form.inert = globalForm.inert = detail.inert = textDetail.inert = busy;
    }
    function globalKeyControls() {
        const profile = state.connections.find((item) => item.id === "public");
        globalKey.disabled = profile?.sources?.api_key === "environment";
        globalKey.required = !profile?.has_api_key;
        globalKey.placeholder = uiText(profile?.has_api_key ? "Configured — leave blank to keep / 已配置，留空保留" : "Enter EcoHash API Key / 输入 EcoHash API Key");
        globalSave.textContent = uiText(globalKey.disabled ? "Verify API Key / 验证 API Key" : "Save and verify API Key / 保存并验证 API Key");
        globalStatus.textContent = uiText(globalKey.disabled ? "Managed by ECOHASH_API_KEY. / 由 ECOHASH_API_KEY 环境变量管理。" : profile?.has_api_key ? "API Key configured; shared by all EcoHash connections. / API Key 已配置，所有 EcoHash 官方连接共用。" : "Enter your EcoHash API Key to get started. / 请先填写 EcoHash API Key。");
    }
    function connectionKeyControls() {
        const profile = state.connections.find((item) => item.id === selectedId);
        const global = selectedId === "public" || isEcoHashUrl(url.value);
        key.parentElement.hidden = global;
        key.disabled = global || profile?.sources?.api_key === "environment";
        key.required = !key.disabled && !(profile && !profile.uses_global_key && profile.has_api_key);
        if (key.required) advanced.open = true;
        source.textContent = [global ? uiText("Uses the global EcoHash API Key. / 使用上方统一配置的全局 API Key。") : "",
            ...Object.entries(profile?.sources || {}).filter(([, src]) => src === "environment").map(([field]) => uiText(`${field}: managed by environment / ${field}：由环境变量管理`))].filter(Boolean).join(" · ");
    }
    form.oninput = () => { dirty = true; connectionKeyControls(); message("Unsaved changes. Save before testing. / 配置有修改，请先保存再测试。"); controls(); };
    consent.onchange = modelInput.oninput = controls;
    textConsent.onchange = textModel.oninput = controls;
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
        id.value = create && value === "__new__" ? `connection-${crypto.randomUUID().slice(0, 8)}` : value;
        name.value = profile?.name || (value === "__new__" ? "" : value);
        url.value = profile?.base_url || (create ? "https://api.ecohash.com/v1" : "");
        key.value = "";
        timeout.value = profile?.timeout || "300";
        url.disabled = value === "public" || profile?.sources?.base_url === "environment";
        timeout.disabled = value === "public" || profile?.sources?.timeout === "environment";
        name.parentElement.hidden = url.parentElement.hidden = advanced.hidden = save.hidden = value === "public";
        name.required = value !== "public";
        url.required = value !== "public";
        advanced.open = false;
        key.placeholder = uiText(profile?.has_api_key && !profile.uses_global_key ? "Configured — leave blank to keep / 已配置，留空保留" : "Enter endpoint API key / 输入端点独立密钥");
        connectionKeyControls();
        models.replaceChildren();
        detail.hidden = !!contextNode && !nodeType(contextNode).includes("Image");
        textDetail.hidden = !!contextNode && !/LLM|VLM/u.test(nodeType(contextNode));
        consent.checked = false;
        modelInput.value = "";
        preview.hidden = true;
        preview.removeAttribute("src");
        textConsent.checked = false;
        textModel.value = "";
        textPreview.hidden = true;
        textPreview.textContent = "";
        message(create ? "Enter a display name and API URL. EcoHash connections use the global API Key. / 填写显示名称和 API 地址，EcoHash 官方连接自动使用全局 API Key。" : state.checked.get(value)?.message || profile?.message || "Connection is missing. Add it with this ID, or choose another connection in the workflow. / 缺少连接，请创建同名连接或在节点中重新选择。");
        controls();
    }
    async function reload(preferred = selectedId) {
        await loadProfiles();
        globalKeyControls();
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
    chooser.onchange = () => { select(chooser.value); if (selectedId !== "public") state.preferred = selectedId; };
    add.onclick = () => select("__new__", true);
    globalForm.onsubmit = (event) => {
        event.preventDefault();
        if (!globalForm.reportValidity()) return;
        operation("Verifying EcoHash API Key… / 正在验证 EcoHash API Key…", async () => {
            try {
                if (!globalKey.disabled && globalKey.value.trim()) await request("/connections/public", "PUT", { api_key: globalKey.value });
                globalKey.value = "";
                await loadProfiles();
                globalKeyControls();
                connectionKeyControls();
                for (const profile of state.connections) if (profile.uses_global_key) invalidateModels(profile.id);
                const checked = await request("/connections/public/test", "POST", {});
                state.checked.set("public", checked);
                const ids = new Set(allNodes().map(connectionId).filter((id) => state.connections.some((p) => p.id === id && p.uses_global_key)));
                if (!creating && !dirty) ids.add(selectedId);
                await Promise.all([...ids].map((id) => loadModels(id).catch((error) => {
                    for (const node of allNodes()) if (connectionId(node) === id) modelError(node, error);
                })));
                for (const node of allNodes()) updateNode(node);
                if (!creating && !dirty && state.models.has(selectedId)) displayModels(state.models.get(selectedId));
                globalStatus.textContent = uiText("EcoHash API Key verified. No inference request was sent. / EcoHash API Key 验证通过，未发送推理请求。");
                message(dirty ? "Unsaved connection changes are preserved. / 尚未保存的连接修改已保留。" : "EcoHash connections now use the global API Key. / EcoHash 官方连接已统一使用全局 API Key。");
            } catch (error) {
                globalStatus.textContent = uiText(error.message);
                throw error;
            }
        });
    };
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
            if (target !== "public") state.preferred = target;
            if (contextNode && isDedicated(nodeType(contextNode)) && allNodes().includes(contextNode) && target !== "public") await applyConnection(contextNode, target);
            await refreshNodes();
            if (!saved.configured) { message(saved.message, true); return; }
            if (target === "public") {
                const checked = await request(`/connections/${encodeURIComponent(target)}/test`, "POST", {});
                state.checked.set(target, checked);
            }
            const result = await loadModels(target);
            displayModels(result);
            for (const node of allNodes()) updateNode(node);
            message(result.error || "Saved and connected; models are ready. No inference request was sent. / 已保存并连接，模型已加载，未发送推理请求。");
        });
    };
    test.onclick = () => operation("Connecting… / 正在检测连接…", async () => {
        const result = await request(`/connections/${encodeURIComponent(selectedId)}/test`, "POST", {});
        state.checked.set(selectedId, result);
        for (const node of allNodes()) if (connectionId(node) === selectedId) updateNode(node);
        message(result.message);
    });
    function displayModels(result) {
        models.replaceChildren(...result.models.map((item) => {
            const row = element("li", item.name === item.id ? item.id : `${item.name} — ${item.id}`);
            row.title = capabilityHint(item, contextNode ? nodeType(contextNode) : "", uiLocale());
            if (contextNode && isDedicated(nodeType(contextNode)) === (selectedId !== "public") && modelsForNode([item], nodeType(contextNode)).length) {
                const use = element("button", "Use on current node / 用于当前节点");
                use.type = "button";
                use.onclick = () => operation("Selecting model… / 正在选择模型…", async () => {
                    await applyConnection(contextNode, selectedId);
                    widget(contextNode, "model").value = item.id;
                    contextNode._ehManualModel = false;
                    updateNode(contextNode);
                    message("Connection and model applied to the current node. / 连接和模型已应用到当前节点。");
                });
                row.append(use);
            }
            return row;
        }));
        const categories = result.models.map((m) => m.category);
        if (categories.length && categories.every(Boolean)) {
            detail.hidden = !!contextNode && !nodeType(contextNode).includes("Image") || !categories.includes("image");
            textDetail.hidden = !!contextNode && !/LLM|VLM/u.test(nodeType(contextNode)) || !categories.some((c) => ["llm", "llm_vision"].includes(c));
        }
    }
    discover.onclick = () => operation("Loading models… / 正在读取模型…", async () => {
        const result = await loadModels(selectedId, true);
        displayModels(result);
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
    complete.onclick = () => operation("Generating text… / 正在生成文本…", async () => {
        const result = await request(`/connections/${encodeURIComponent(selectedId)}/chat-test`, "POST", { model: textModel.value.trim(), confirm_inference: textConsent.checked });
        textPreview.textContent = result.text;
        textPreview.hidden = false;
        textConsent.checked = false;
        message("Text inference passed. / 文本推理成功。");
    });
    reload().catch((error) => message(error.message, true));
}

function showManager(id = "public", node) {
    const existing = document.querySelector("dialog.ecohash-dialog");
    if (existing) { existing.focus(); return; }
    const dialog = element("dialog", undefined, "ecohash-dialog");
    dialog.setAttribute("aria-label", uiText("EcoHash connections / 连接设置"));
    const root = element("div");
    dialog.append(root);
    document.body.append(dialog);
    mountManager(root, id, () => dialog.close(), node);
    dialog.onclose = () => dialog.remove();
    dialog.showModal();
}

function hookWidget(node, name, fn) {
    const item = widget(node, name);
    if (!item) return;
    const previous = item.callback;
    item.callback = function (...args) { previous?.apply(this, args); fn(...args); };
}

function addUiWidget(node, ...args) {
    const item = node.addWidget(...args);
    // LiteGraph saves the widget property, while the API prompt builder checks
    // options.serialize. Apply this only to our UI widgets: ComfyUI's seed
    // control also has options.serialize=false but must persist in workflows.
    item.serialize = false;
    return item;
}

app.registerExtension({
    name: "EcoHash.Connections",
    beforeConfigureGraph(data) { migrateVideoWorkflow(data); },
    commands: [{ id: "EcoHash.ManageConnections", label: uiText("EcoHash connections / 连接设置"), function: () => showManager() }],
    menuCommands: [{ path: ["Extensions", "EcoHash"], commands: ["EcoHash.ManageConnections"] }],
    setup() {
        const style = element("link");
        style.rel = "stylesheet";
        style.href = new URL("./ecohash.css", import.meta.url).href;
        document.head.append(style);
        app.extensionManager.registerSidebarTab({ id: "ecohash-connections", icon: "pi pi-cloud", title: "EcoHash", tooltip: uiText("EcoHash connections / 连接设置"), type: "custom", render: (root) => mountManager(root, state.preferred || "public") });
        loadProfiles().then(() => Promise.all([...new Set(allNodes().map(connectionId))].map((id) => loadModels(id).catch(() => null))))
            .then(() => allNodes().forEach(updateNode)).catch(() => {});
        let activeNode;
        function executionStatus(node, message) {
            const status = widget(node, "Execution status");
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
        api.addEventListener("ecohash_video_progress", (event) => {
            const detail = event.detail;
            const node = app.graph?.getNodeById(detail?.node);
            const task = widget(node || {}, "Video task");
            if (!task) return;
            const names = { queued: "Queued / 排队中", processing: "Generating / 生成中", in_progress: "Generating / 生成中", running: "Generating / 生成中", completed: "Completed / 已完成", failed: "Failed / 失败" };
            const percent = Number.isFinite(detail.progress) ? ` ${detail.progress}%` : "";
            task.value = `${uiText(names[detail.status] || String(detail.status))}${percent} · ${detail.job_id}`;
            node.setDirtyCanvas?.(true, true);
        });
    },
    nodeCreated(node) {
        const type = nodeType(node);
        if (!type?.startsWith("EcoHash")) return;
        if (type.endsWith("VideoGenerate")) { node.properties ??= {}; node.properties.ecohash_video_schema = 3; }
        const primary = [];
        if (isDedicated(type)) primary.push(addUiWidget(node, "combo", "Select connection", chooseConnection, async (label) => {
            const profile = state.connections.find((p) => connectionLabel(p) === label);
            if (!profile) return;
            try { await applyConnection(node, profile.id); }
            catch (error) { modelError(node, error); }
        }, { values: [chooseConnection], serialize: false }));
        if (isDedicated(type)) primary.push(addUiWidget(node, "combo", "Choose discovered model", chooseModel, (value) => {
            node._ehManualModel = value === manualModel;
            if (value === manualModel || value === chooseModel) { updateNode(node); return; }
            const model = widget(node, "model");
            model.value = value;
            model.callback?.(value);
            updateNode(node);
        }, { values: [chooseModel, manualModel], serialize: false }));
        addUiWidget(node, "button", "Connections", null, () => showManager(connectionId(node), node), { serialize: false });
        if (type.endsWith("TTS")) addUiWidget(node, "combo", "Choose voice", manualVoice, (value) => {
            node._ehManualVoice = value === manualVoice;
            if (value !== manualVoice) widget(node, "voice").value = value;
            updateNode(node);
        }, { values: [manualVoice], serialize: false });
        const refresh = addUiWidget(node, "button", "Refresh models", null, async () => {
            refresh.options.disabled = true;
            node.setDirtyCanvas?.(true, true);
            try {
                await loadProfiles();
                const result = await loadModels(connectionId(node), true);
                updateNode(node);
                if (result.error) modelError(node, new Error(uiText(result.error)));
            } catch (error) { modelError(node, error); }
            finally { refresh.options.disabled = false; }
            node.setDirtyCanvas?.(true, true);
        }, { serialize: false });
        const status = addUiWidget(node, "text", "Execution status", "", () => {}, { serialize: false });
        status.options.read_only = true;
        if (type.endsWith("VideoGenerate")) {
            addUiWidget(node, "toggle", "Advanced settings", false, (value) => { node._ehAdvanced = value; updateNode(node); }, { serialize: false });
            const task = addUiWidget(node, "text", "Video task", uiText("Job ID appears here after submission; copy it to job_id to resume. / 提交后显示任务 ID；复制到 job_id 可恢复查询。"), () => {}, { serialize: false });
            task.options.read_only = true;
        }
        // UI-only selectors may move without changing serialized core-widget order.
        node.widgets = [...primary, ...node.widgets.filter((item) => !primary.includes(item))];
        const labels = { "Connections": "连接设置", "Refresh models": "刷新模型", "Select connection": "连接", "Choose discovered model": "模型", "Choose voice": "音色", "Video task": "视频任务", "Advanced settings": "高级设置", "Execution status": "运行状态" };
        for (const item of node.widgets || []) {
            if (item.options?.serialize === false) {
                item.label = uiText(labels[item.name] ? `${item.name} / ${labels[item.name]}` : item.name);
            }
        }
        hookWidget(node, "connection", async () => {
            try { await applyConnection(node, connectionId(node), false); }
            catch (error) { modelError(node, error); }
        });
        hookWidget(node, "model", () => {
            if (type.endsWith("TTS")) {
                const selected = state.models.get(connectionId(node))?.models?.find((item) => item.id === widget(node, "model")?.value);
                if (selected?.voices?.length) widget(node, "voice").value = selected.voices[0];
                else widget(node, "voice").value = "";
            }
            updateNode(node);
        });
        for (const name of ["mode", "size", "resolution"]) hookWidget(node, name, () => updateNode(node));
        const configured = node.onConfigure;
        node.onConfigure = function (...args) {
            this._ehRestored = true;
            configured?.apply(this, args);
            updateNode(this);
            if (this.properties?.ecohash_migration_warning) widget(this, "Execution status").value = uiText("Migrated native workflow: verify the deployment supports the platform video API before generating. / 已迁移原生视频工作流：生成前需确认实例支持平台的视频生成接口。");
        };
        updateNode(node);
        loadProfiles().then(async () => {
            const preferred = isDedicated(type) && !node._ehRestored ? defaultConnection(state.connections, state.preferred) : null;
            if (preferred) {
                const result = await loadModels(preferred);
                if (!node._ehRestored && (!result.models.length || modelsForNode(result.models, type).length)) await applyConnection(node, preferred);
            } else await loadModels(connectionId(node));
            updateNode(node);
        }).catch((error) => modelError(node, error));
    },
});
