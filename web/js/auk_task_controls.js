import { app } from "../../../scripts/app.js";

let guides = {};
let aliases = {};
const guideUrl = new URL("../task_guides.json", import.meta.url);
const aliasesUrl = new URL("../legacy_widget_values.json", import.meta.url);
guideUrl.searchParams.set("v", "english-2");
aliasesUrl.searchParams.set("v", "english-2");
Promise.all([guideUrl, aliasesUrl].map(async (url) => {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }))
    .then(([value, legacy]) => {
        guides = value;
        aliases = legacy;
        for (const node of app.graph?._nodes || []) node.aukRefreshTaskGuide?.();
    })
    .catch((error) => console.error("AuK task guide failed to load", error));

function renderGuide(container, label) {
    const guide = guides[label];
    if (!guide) {
        container.textContent = "Loading AuK task requirements…";
        return;
    }
    container.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = `Usage & tuning · ${label}`;
    const requirement = document.createElement("div");
    requirement.textContent = guide.requirement;
    const primary = document.createElement("div");
    primary.textContent = `1. ${guide.primary_label}: ${guide.primary_help}`;
    const secondary = document.createElement("div");
    secondary.textContent = `2. ${guide.secondary_label}: ${guide.secondary_help}`;
    primary.style.marginTop = "6px";
    secondary.style.marginTop = "6px";
    const example = document.createElement("div");
    example.textContent = `Example: ${guide.example}`;
    const note = document.createElement("div");
    note.textContent = `Tips: ${guide.note}`;
    note.style.marginTop = "6px";
    note.style.opacity = "0.78";
    container.append(title, requirement, primary, secondary, example, note);
}

app.registerExtension({
    name: "T8star.AuKTaskGuide",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "AuKGenerateEdit") return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            const taskWidget = this.widgets?.find((widget) => widget.name === "task");
            if (!taskWidget || typeof this.addDOMWidget !== "function") return result;

            const container = document.createElement("div");
            Object.assign(container.style, {
                boxSizing: "border-box",
                width: "100%",
                height: "100%",
                minHeight: "0",
                overflow: "auto",
                padding: "10px 12px",
                color: "#1f2937",
                background: "#fff3f8",
                border: "1px solid #ff9dc8",
                borderRadius: "8px",
                fontSize: "12px",
                lineHeight: "1.55",
                whiteSpace: "normal",
            });
            const guideWidget = this.addDOMWidget("auk_task_guide", "div", container, {
                serialize: false,
                hideOnZoom: false,
                getMinHeight: () => 250,
                getHeight: () => 250,
            });
            guideWidget.serialize = false;
            guideWidget.options = { ...(guideWidget.options || {}), serialize: false };

            this.aukRefreshTaskGuide = () => {
                // Schemas accept upstream values for API compatibility; the UI
                // migrates them and presents only English choices.
                for (const name of ["task", "duration_mode"]) {
                    const widget = this.widgets?.find((entry) => entry.name === name);
                    const values = aliases[name];
                    if (!widget || !values) continue;
                    if (Object.hasOwn(values, widget.value)) widget.value = values[widget.value];
                    if (Array.isArray(widget.options?.values)) {
                        widget.options.values = widget.options.values.filter((value) => !Object.hasOwn(values, value));
                    }
                }
                const guide = guides[taskWidget.value];
                if (guide) {
                    for (const [name, number] of [["primary", 1], ["secondary", 2]]) {
                        const widget = this.widgets?.find((entry) => entry.name === name);
                        if (!widget) continue;
                        widget.label = `${number}. ${guide[`${name}_label`]}`;
                        widget.options = { ...(widget.options || {}), tooltip: guide[`${name}_help`] };
                        if (widget.inputEl) {
                            widget.inputEl.placeholder = guide[`${name}_help`];
                            widget.inputEl.title = guide[`${name}_help`];
                            widget.inputEl.setAttribute("aria-label", widget.label);
                        }
                    }
                }
                renderGuide(container, taskWidget.value);
                const durationWidget = this.widgets?.find((widget) => widget.name === "duration_mode");
                if (!durationWidget) return;
                const button = document.createElement("button");
                button.type = "button";
                button.textContent = "↻ Adapt duration automatically";
                button.title = "TTS uses target text; editing uses the actual input and task rules, ignoring connected Float.";
                Object.assign(button.style, {
                    display: "block", marginBottom: "6px",
                    marginTop: "6px", padding: "4px 10px", border: "1px solid #ff9dc8",
                    borderRadius: "6px", background: "#ffffff", color: "#b31765", cursor: "pointer",
                });
                button.onclick = (event) => {
                    event.stopPropagation();
                    const secondsWidget = this.widgets?.find((widget) => widget.name === "generation_seconds");
                    if (secondsWidget && (!Number.isFinite(Number(secondsWidget.value)) ||
                        Number(secondsWidget.value) < 0.2 || Number(secondsWidget.value) > 30)) {
                        secondsWidget.value = 3;
                    }
                    durationWidget.value = "Automatic adaptation (task rules)";
                    durationWidget.callback?.(durationWidget.value);
                    app.graph?.setDirtyCanvas(true, true);
                };
                container.prepend(button);
            };
            const originalCallback = taskWidget.callback;
            taskWidget.callback = (value, ...args) => {
                const callbackResult = originalCallback?.call(taskWidget, value, ...args);
                this.aukRefreshTaskGuide();
                return callbackResult;
            };
            this.aukRefreshTaskGuide();
            return result;
        };
    },
    loadedGraphNode(node) {
        node.aukRefreshTaskGuide?.();
    },
});
