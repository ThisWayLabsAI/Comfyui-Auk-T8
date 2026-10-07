const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");
const guides = JSON.parse(fs.readFileSync(path.join(root, "web/task_guides.json"), "utf8"));
const aliases = JSON.parse(fs.readFileSync(path.join(root, "web/legacy_widget_values.json"), "utf8"));
const source = fs.readFileSync(path.join(root, "web/js/auk_task_controls.js"), "utf8")
    .replace(/^import .*;\r?\n/, "")
    .replaceAll("import.meta.url", '"https://example.invalid/web/js/auk_task_controls.js"');

function element() {
    return {
        style: {}, children: [], textContent: "",
        replaceChildren() { this.children = []; this.textContent = ""; },
        append(...nodes) { this.children.push(...nodes); },
        prepend(node) { this.children.unshift(node); },
    };
}

async function setup(loadImmediately) {
    let extension;
    let resolveFetch;
    const ready = new Promise((resolve) => { resolveFetch = resolve; });
    const app = {
        graph: { _nodes: [], setDirtyCanvas() {} },
        registerExtension(value) { extension = value; },
    };
    vm.runInNewContext(source, {
        app, URL, console,
        document: { createElement: element },
        fetch: async (url) => {
            await ready;
            return { ok: true, json: async () => url.pathname.endsWith("task_guides.json") ? guides : aliases };
        },
    });
    const flush = () => new Promise((resolve) => setImmediate(resolve));
    if (loadImmediately) { resolveFetch(); await flush(); }
    class Node {
        constructor() {
            this.widgets = [
                { name: "task", value: "描述生成语音", options: { values: [...Object.keys(guides), ...Object.keys(aliases.task)] } },
                { name: "duration_mode", value: "手动指定", options: { values: [...Object.values(aliases.duration_mode), ...Object.keys(aliases.duration_mode)] } },
                { name: "generation_seconds", value: 99 },
            ];
        }
        addDOMWidget(name, type, container) { this.container = container; return {}; }
    }
    await extension.beforeRegisterNodeDef(Node, { name: "AuKGenerateEdit" });
    const node = new Node();
    app.graph._nodes.push(node);
    node.onNodeCreated();
    if (!loadImmediately) { resolveFetch(); await flush(); }
    return { node, extension };
}

for (const immediate of [true, false]) {
    test(`upstream widget values migrate with metadata loaded ${immediate ? "before" : "after"} node creation`, async () => {
        const { node, extension } = await setup(immediate);
        assert.equal(node.widgets[0].value, "Instruction TTS");
        assert.equal(node.widgets[1].value, "Manual duration");
        assert.equal(node.widgets[0].options.values.length, 17);
        assert.ok(node.widgets[0].options.values.every((value) => !Object.hasOwn(aliases.task, value)));
        assert.equal(node.widgets[1].options.values.length, 3);
        assert.equal(node.container.children[1].textContent, "Official usage · Instruction TTS");
        // Loading a graph reapplies serialized values after node creation.
        for (const [legacy, english] of Object.entries(aliases.task)) {
            node.widgets[0].value = legacy;
            extension.loadedGraphNode(node);
            assert.equal(node.widgets[0].value, english);
            assert.equal(node.container.children[1].textContent, `Official usage · ${english}`);
        }
        node.container.children[0].onclick({ stopPropagation() {} });
        assert.equal(node.widgets[1].value, "Automatic adaptation (task rules)");
        assert.equal(node.widgets[2].value, 3);
        assert.equal(node.container.children[0].textContent, "↻ Adapt duration automatically");
    });
}
