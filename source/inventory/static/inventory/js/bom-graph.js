/* ==========================================================================
   bom-graph.js — the assembly map of the bill of materials
   Place this file at: inventory/static/inventory/js/bom-graph.js

   The script reads a graph from a JSON script tag, gives the layout to
   dagre, and puts each node on the canvas as an HTML element. The edges
   are one SVG layer below the nodes.

   HTML that the script needs:
       <div class="graph" data-graph>
         <div class="graph__view">
           <div class="graph__canvas">
             <svg class="graph__edges"></svg>
           </div>
         </div>
       </div>
       <script type="application/json" id="bom-graph-data"> ... </script>

   Data:
       nodes  id, name, code, kind (kit|sub|part), status, count
       edges  from, to, qty, limit (optional)

   The nodes stay HTML, thus all colors come from the stylesheet and a
   later function (a menu, a form, a drag) needs no new renderer.
   ========================================================================== */
(function () {
    "use strict";

    var host = document.querySelector("[data-graph]");
    var src = document.getElementById("bom-graph-data");
    if (!host || !src || !window.dagre) { return; }

    var data = JSON.parse(src.textContent);
    var view = host.querySelector(".graph__view");
    var canvas = host.querySelector(".graph__canvas");
    var edges = host.querySelector(".graph__edges");
    var NS = "http://www.w3.org/2000/svg";

    /* ---- 1. Make the nodes, then measure them --------------------- */
    var els = {};
    data.nodes.forEach(function (n) {
        var el = document.createElement("div");
        el.className = "gnode gnode--" + (n.kind || "part");
        el.setAttribute("data-id", n.id);
        el.setAttribute("tabindex", "0");
        el.innerHTML =
            '<span class="gnode__top">' +
            '<span class="gnode__name"></span>' +
            '<span class="status status--' + (n.status || "idle") + '"></span>' +
            "</span>" +
            '<span class="gnode__meta">' +
            '<span class="gnode__code"></span>' +
            "</span>";
        el.querySelector(".gnode__name").textContent = n.name;
        el.querySelector(".status").textContent = n.count;
        el.querySelector(".gnode__code").textContent = n.code;
        canvas.appendChild(el);
        els[n.id] = el;
    });

    /* ---- 2. Give the layout to dagre ------------------------------ */
    var g = new dagre.graphlib.Graph({ multigraph: true });
    g.setGraph({
        rankdir: data.direction || "LR",
        nodesep: 18,
        ranksep: 72,
        marginx: 24,
        marginy: 24
    });
    g.setDefaultEdgeLabel(function () { return {}; });

    data.nodes.forEach(function (n) {
        g.setNode(n.id, {
            width: els[n.id].offsetWidth,
            height: els[n.id].offsetHeight
        });
    });
    data.edges.forEach(function (e, i) {
        g.setEdge(e.from, e.to, { data: e }, "e" + i);
    });

    dagre.layout(g);

    /* ---- 3. Put each node on the canvas --------------------------- */
    g.nodes().forEach(function (id) {
        var n = g.node(id);
        var el = els[id];
        el.style.left = (n.x - n.width / 2) + "px";
        el.style.top = (n.y - n.height / 2) + "px";
    });

    var size = g.graph();
    canvas.style.width = size.width + "px";
    canvas.style.height = size.height + "px";
    edges.setAttribute("width", size.width);
    edges.setAttribute("height", size.height);

    /* ---- 4. Draw one curve for each edge --------------------------- */
    var lr = (data.direction || "LR") === "LR";

    g.edges().forEach(function (k) {
        var e = g.edge(k);
        var a = g.node(k.v);
        var b = g.node(k.w);
        var x1 = lr ? a.x + a.width / 2 : a.x;
        var y1 = lr ? a.y : a.y + a.height / 2;
        var x2 = lr ? b.x - b.width / 2 : b.x;
        var y2 = lr ? b.y : b.y - b.height / 2;
        var d = lr
            ? "M" + x1 + "," + y1 + "C" + (x1 + 40) + "," + y1 +
              " " + (x2 - 40) + "," + y2 + " " + x2 + "," + y2
            : "M" + x1 + "," + y1 + "C" + x1 + "," + (y1 + 40) +
              " " + x2 + "," + (y2 - 40) + " " + x2 + "," + y2;

        var path = document.createElementNS(NS, "path");
        path.setAttribute("class", "gedge" + (e.data.limit ? " is-limit" : ""));
        path.setAttribute("d", d);
        path.setAttribute("data-from", k.v);
        path.setAttribute("data-to", k.w);
        edges.appendChild(path);

        if (e.data.qty) {
            var t = document.createElementNS(NS, "text");
            t.setAttribute("class", "gedge__qty");
            t.setAttribute("x", (x1 + x2) / 2);
            t.setAttribute("y", (y1 + y2) / 2 - 6);
            t.setAttribute("text-anchor", "middle");
            t.textContent = e.data.qty;
            edges.appendChild(t);
        }
    });

    /* ---- 5. Pan, zoom and fit -------------------------------------- */
    var tx = 0, ty = 0, scale = 1;

    function apply() {
        canvas.style.transform =
            "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
        view.style.backgroundSize = (18 * scale) + "px " + (18 * scale) + "px";
        view.style.backgroundPosition = tx + "px " + ty + "px";
    }

    function fit() {
        var w = view.clientWidth, h = view.clientHeight;
        scale = Math.min(1, w / size.width, h / size.height);
        tx = (w - size.width * scale) / 2;
        ty = (h - size.height * scale) / 2;
        apply();
    }

    function zoom(step) {
        scale = Math.min(2, Math.max(0.3, scale + step));
        apply();
    }

    view.addEventListener("wheel", function (ev) {
        ev.preventDefault();
        zoom(ev.deltaY > 0 ? -0.08 : 0.08);
    }, { passive: false });

    view.addEventListener("pointerdown", function (ev) {
        if (ev.target.closest(".gnode")) { return; }
        var x0 = ev.clientX - tx, y0 = ev.clientY - ty;
        view.setPointerCapture(ev.pointerId);
        view.classList.add("is-panning");

        function move(m) { tx = m.clientX - x0; ty = m.clientY - y0; apply(); }
        function up() {
            view.classList.remove("is-panning");
            view.removeEventListener("pointermove", move);
            view.removeEventListener("pointerup", up);
        }
        view.addEventListener("pointermove", move);
        view.addEventListener("pointerup", up);
    });

    host.querySelectorAll("[data-graph-zoom]").forEach(function (b) {
        b.addEventListener("click", function () {
            var v = b.getAttribute("data-graph-zoom");
            if (v === "fit") { fit(); } else { zoom(Number(v)); }
        });
    });

    /* ---- 6. Select a node and light its edges ---------------------- */
    canvas.addEventListener("click", function (ev) {
        var el = ev.target.closest(".gnode");
        if (!el) { return; }
        var id = el.getAttribute("data-id");
        var on = !el.classList.contains("is-active");

        canvas.querySelectorAll(".gnode").forEach(function (n) {
            n.classList.remove("is-active");
        });
        edges.querySelectorAll(".gedge").forEach(function (p) {
            p.classList.remove("is-lit");
        });
        if (!on) { return; }

        el.classList.add("is-active");
        edges.querySelectorAll(".gedge").forEach(function (p) {
            if (p.getAttribute("data-from") === id ||
                p.getAttribute("data-to") === id) {
                p.classList.add("is-lit");
            }
        });
    });

    fit();
    window.addEventListener("resize", fit);
}());