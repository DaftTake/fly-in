// Fly-In Time-Expanded Dijkstra - Galles AnimationLibrary Integration
// Complete rewrite: dynamic table, visible priority queue, cleaner layout

// Layout constants
var GRAPH_Y_OFFSET = 30;
var MSG_X = 20;
var MSG_Y = 10;

// Table layout (left side, below graph)
var TBL_X = 30;
var TBL_Y = 200;
var TBL_ROW_H = 22;
var TBL_COL_W = [100, 50, 50, 110]; // State, Known, Cost, Parent

// Frontier display (center, below graph)  
var FQ_X = 380;
var FQ_Y = 200;

// Reservations display (right side, below graph)
var RES_X = 700;
var RES_Y = 200;

var EDGE_COLOR = "#000000";

function FlyIn(am, w, h) {
    this.init(am, w, h);
}

FlyIn.prototype = new Algorithm();
FlyIn.prototype.constructor = FlyIn;
FlyIn.superclass = Algorithm.prototype;

FlyIn.prototype.addControls = function() {
    this.startButton = addControlToAlgorithmBar("Button", "Run Fly-In (2 Drones)");
    this.startButton.onclick = this.startCallback.bind(this);
}

FlyIn.prototype.init = function(am, w, h) {
    FlyIn.superclass.init.call(this, am, w, h);
    this.addControls();
    this.setup();
}

FlyIn.prototype.setup = function() {
    this.commands = new Array();
    this.nextIndex = 0;

    // Status message label
    this.msgID = this.nextIndex++;
    this.cmd("CreateLabel", this.msgID, "Click 'Run Fly-In' to start the algorithm.", MSG_X, MSG_Y, 0);

    // --- Draw the physical graph ---
    this.graphNodes = {
        "START": { x: 80,  y: 80 + GRAPH_Y_OFFSET,  max: 2, cost: 1 },
        "A1":    { x: 220, y: 40 + GRAPH_Y_OFFSET,   max: 1, cost: 1 },
        "B1":    { x: 220, y: 120 + GRAPH_Y_OFFSET,  max: 1, cost: 1 },
        "A2":    { x: 370, y: 40 + GRAPH_Y_OFFSET,   max: 1, cost: 1 },
        "B2":    { x: 370, y: 120 + GRAPH_Y_OFFSET,  max: 1, cost: 1 },
        "MID":   { x: 520, y: 80 + GRAPH_Y_OFFSET,   max: 2, cost: 1 },
        "END":   { x: 670, y: 80 + GRAPH_Y_OFFSET,   max: 2, cost: 1 }
    };

    this.graphEdges = [
        ["START", "A1"], ["START", "B1"],
        ["A1", "A2"], ["B1", "B2"],
        ["A2", "MID"], ["B2", "MID"],
        ["MID", "END"]
    ];

    // Create circle for each node
    for (var key in this.graphNodes) {
        var n = this.graphNodes[key];
        n.cId = this.nextIndex++;
        this.cmd("CreateCircle", n.cId, key, n.x, n.y);
        // Meta label showing capacity
        n.metaId = this.nextIndex++;
        this.cmd("CreateLabel", n.metaId, "max=" + n.max, n.x, n.y + 28, 0);
        this.cmd("SetForegroundColor", n.metaId, "#888888");
    }

    // Draw directed edges with cost labels
    for (var i = 0; i < this.graphEdges.length; i++) {
        var from = this.graphEdges[i][0];
        var to = this.graphEdges[i][1];
        this.cmd("Connect", this.graphNodes[from].cId, this.graphNodes[to].cId,
                 EDGE_COLOR, 0, 1, "cost=" + this.graphNodes[to].cost);
    }

    // --- Section Headers (static) ---
    // Table header
    this.tblHeaderIDs = [];
    var headers = ["Node (Zone, t)", "Known", "Cost", "Via"];
    var xOff = 0;
    for (var i = 0; i < headers.length; i++) {
        var hId = this.nextIndex++;
        this.tblHeaderIDs.push(hId);
        this.cmd("CreateLabel", hId, headers[i], TBL_X + xOff + TBL_COL_W[i]/2, TBL_Y, 0);
        this.cmd("SetForegroundColor", hId, "#AAAAAA");
        xOff += TBL_COL_W[i];
    }

    // Frontier header
    this.fqHeaderID = this.nextIndex++;
    this.cmd("CreateLabel", this.fqHeaderID, "Priority Queue (Frontier)", FQ_X + 100, FQ_Y, 0);
    this.cmd("SetForegroundColor", this.fqHeaderID, "#AAAAAA");

    // Reservations header
    this.resHeaderID = this.nextIndex++;
    this.cmd("CreateLabel", this.resHeaderID, "Committed Reservations", RES_X + 80, RES_Y, 0);
    this.cmd("SetForegroundColor", this.resHeaderID, "#AAAAAA");

    this.animationManager.StartNewAnimation(this.commands);
    this.animationManager.skipForward();
    this.animationManager.clearHistory();
}

FlyIn.prototype.startCallback = function(event) {
    this.implementAction(this.doFlyIn.bind(this), "");
}

// Helper: format a state string for display
FlyIn.prototype.fmt = function(stateStr) {
    var p = stateStr.split(",");
    return "(" + p[0] + ", t=" + p[1] + ")";
}

// Helper: format frontier for display
FlyIn.prototype.fmtFrontier = function(frontier) {
    var items = [];
    // Show at most 8 items to fit on screen
    var limit = Math.min(frontier.length, 8);
    for (var i = 0; i < limit; i++) {
        items.push(this.fmt(frontier[i].state) + ":" + frontier[i].cost);
    }
    if (frontier.length > limit) {
        items.push("... +" + (frontier.length - limit) + " more");
    }
    return items.join("\n");
}

FlyIn.prototype.doFlyIn = function() {
    this.commands = new Array();

    var zoneRes = {};   // global zone reservations: "ZONE,TURN" -> count
    var edgeRes = {};   // global edge reservations
    var numDrones = 2;
    var context = this;

    // Track all dynamically created IDs so we can clean up
    var allDynIDs = [];

    // Frontier display labels (we'll reuse/recreate each step)
    var fqLabelIDs = [];

    // Reservation display labels
    var resLabelIDs = [];

    // ===== MAIN LOOP: one Dijkstra per drone =====
    for (var d = 1; d <= numDrones; d++) {
        var droneName = "Drone " + d;
        var droneColor = d === 1 ? "#2196F3" : "#FF9800"; // blue, orange

        // --- Announce drone ---
        this.cmd("SetText", this.msgID, "=== Planning path for " + droneName + " ===");
        this.cmd("Step");

        // --- Dijkstra state ---
        var dist = {};
        var parentMap = {};
        var finalized = {};
        var frontier = [];
        var pathFound = null;

        // Seed with START at t=0
        var startState = "START,0";
        dist[startState] = 0;
        parentMap[startState] = null;
        frontier.push({ state: startState, cost: 0 });

        // --- Dynamic table: maps stateStr -> { row, ids: {state, known, cost, parent} } ---
        var tableRows = {};
        var tableRowCount = 0;

        // Create the initial row for START,0
        function addTableRow(stateStr, costVal, parentStr) {
            if (tableRows[stateStr]) return;
            var row = tableRowCount;
            tableRowCount++;
            var y = TBL_Y + (row + 1) * TBL_ROW_H;
            var ids = {
                state:  context.nextIndex++,
                known:  context.nextIndex++,
                cost:   context.nextIndex++,
                parent: context.nextIndex++
            };
            var xOff = 0;
            context.cmd("CreateRectangle", ids.state, context.fmt(stateStr),
                        TBL_COL_W[0], TBL_ROW_H, TBL_X + xOff + TBL_COL_W[0]/2, y);
            xOff += TBL_COL_W[0];
            context.cmd("CreateRectangle", ids.known, "",
                        TBL_COL_W[1], TBL_ROW_H, TBL_X + xOff + TBL_COL_W[1]/2, y);
            xOff += TBL_COL_W[1];
            context.cmd("CreateRectangle", ids.cost, String(costVal),
                        TBL_COL_W[2], TBL_ROW_H, TBL_X + xOff + TBL_COL_W[2]/2, y);
            xOff += TBL_COL_W[2];
            context.cmd("CreateRectangle", ids.parent, parentStr || "-",
                        TBL_COL_W[3], TBL_ROW_H, TBL_X + xOff + TBL_COL_W[3]/2, y);

            tableRows[stateStr] = { row: row, ids: ids };
            allDynIDs.push(ids.state, ids.known, ids.cost, ids.parent);
        }

        function updateFrontierDisplay() {
            // Clear old frontier labels
            for (var fi = 0; fi < fqLabelIDs.length; fi++) {
                context.cmd("Delete", fqLabelIDs[fi]);
            }
            fqLabelIDs = [];

            // Sort frontier for display
            var sorted = frontier.slice().sort(function(a, b) { return a.cost - b.cost; });
            var limit = Math.min(sorted.length, 12);
            for (var fi = 0; fi < limit; fi++) {
                var lId = context.nextIndex++;
                var y = FQ_Y + (fi + 1) * TBL_ROW_H;
                var txt = context.fmt(sorted[fi].state) + "  cost=" + sorted[fi].cost;
                context.cmd("CreateRectangle", lId, txt, 260, TBL_ROW_H, FQ_X + 130, y);
                if (fi === 0) {
                    // Highlight the top of queue (will be popped next)
                    context.cmd("SetBackgroundColor", lId, "#E3F2FD");
                }
                fqLabelIDs.push(lId);
                allDynIDs.push(lId);
            }
            if (sorted.length > limit) {
                var lId = context.nextIndex++;
                context.cmd("CreateLabel", lId, "... +" + (sorted.length - limit) + " more",
                            FQ_X + 130, FQ_Y + (limit + 1) * TBL_ROW_H, 0);
                context.cmd("SetForegroundColor", lId, "#999999");
                fqLabelIDs.push(lId);
                allDynIDs.push(lId);
            }
        }

        // Show initial state
        addTableRow(startState, 0, "-");
        updateFrontierDisplay();
        this.cmd("SetText", this.msgID, droneName + ": Start at (START, t=0) with cost 0");
        this.cmd("Step");

        // --- Dijkstra main loop ---
        while (frontier.length > 0) {
            // Sort and pop cheapest
            frontier.sort(function(a, b) { return a.cost - b.cost; });
            var curr = frontier.shift();

            if (finalized[curr.state]) continue;
            finalized[curr.state] = true;

            var parts = curr.state.split(",");
            var zone = parts[0];
            var turn = parseInt(parts[1]);

            // Update table: mark as Known
            var tRow = tableRows[curr.state];
            if (tRow) {
                this.cmd("SetText", tRow.ids.known, "YES");
                this.cmd("SetBackgroundColor", tRow.ids.known, "#C8E6C9");
                this.cmd("SetBackgroundColor", tRow.ids.state, "#E8F5E9");
            }

            // Highlight the physical node
            this.cmd("SetHighlight", this.graphNodes[zone].cId, 1);
            this.cmd("SetText", this.msgID, droneName + ": POP " + this.fmt(curr.state) +
                     " - cost " + curr.cost + " (cheapest in queue)");
            updateFrontierDisplay();
            this.cmd("Step");
            this.cmd("SetHighlight", this.graphNodes[zone].cId, 0);

            // Check if we reached END
            if (zone === "END") {
                pathFound = curr.state;
                this.cmd("SetText", this.msgID, droneName + ": REACHED END at turn " + turn + "!");
                this.cmd("Step");
                break;
            }

            // --- Expand neighbors (directed edges: forward only) ---
            var neighbors = [];
            for (var i = 0; i < this.graphEdges.length; i++) {
                if (this.graphEdges[i][0] === zone) neighbors.push(this.graphEdges[i][1]);
                // No backward edges: drones only fly forward through the airspace
            }
            neighbors.push(zone); // "wait" action

            for (var ni = 0; ni < neighbors.length; ni++) {
                var nb = neighbors[ni];
                var isWait = (nb === zone);
                var moveCost = isWait ? 1 : this.graphNodes[nb].cost;
                var arrival = turn + moveCost;
                var nState = nb + "," + arrival;

                if (finalized[nState]) continue;

                // --- Check reservations ---
                var blocked = null;

                // Zone capacity check
                var zKey = nState;
                var zOcc = zoneRes[zKey] || 0;
                if (zOcc >= this.graphNodes[nb].max) {
                    blocked = "zone " + nb + " full at t=" + arrival;
                }

                // Edge capacity check (only for actual moves)
                if (!isWait && !blocked) {
                    var edgeArr = [zone, nb].sort();
                    var edgeKey = edgeArr[0] + "-" + edgeArr[1];
                    for (var t = turn; t < arrival; t++) {
                        var eOcc = edgeRes[edgeKey + "," + t] || 0;
                        if (eOcc >= 1) {
                            blocked = "edge " + zone + "->" + nb + " busy at t=" + t;
                            break;
                        }
                    }
                }

                if (blocked) {
                    // Flash red on the node
                    this.cmd("SetHighlight", this.graphNodes[nb].cId, 1);
                    this.cmd("SetHighlightColor", this.graphNodes[nb].cId, "#FF0000");
                    this.cmd("SetText", this.msgID, droneName + ": BLOCKED -> " +
                             this.fmt(nState) + " (" + blocked + ")");
                    this.cmd("Step");
                    this.cmd("SetHighlight", this.graphNodes[nb].cId, 0);
                    this.cmd("SetHighlightColor", this.graphNodes[nb].cId, "#0000FF");
                    continue;
                }

                // --- Relaxation ---
                var newCost = curr.cost + moveCost;

                if (dist[nState] === undefined || newCost < dist[nState]) {
                    dist[nState] = newCost;
                    parentMap[nState] = curr.state;

                    // Update or add table row
                    if (!tableRows[nState]) {
                        addTableRow(nState, newCost, this.fmt(curr.state));
                    } else {
                        this.cmd("SetText", tableRows[nState].ids.cost, String(newCost));
                        this.cmd("SetText", tableRows[nState].ids.parent, this.fmt(curr.state));
                    }

                    // Highlight the cost cell being updated
                    if (tableRows[nState]) {
                        this.cmd("SetBackgroundColor", tableRows[nState].ids.cost, "#FFF9C4");
                    }

                    // Update frontier
                    var found = false;
                    for (var fi = 0; fi < frontier.length; fi++) {
                        if (frontier[fi].state === nState) {
                            frontier[fi].cost = newCost;
                            found = true;
                            break;
                        }
                    }
                    if (!found) frontier.push({ state: nState, cost: newCost });

                    var action = isWait ? "WAIT" : "MOVE";
                    this.cmd("SetHighlight", this.graphNodes[nb].cId, 1);
                    this.cmd("SetText", this.msgID, droneName + ": " + action + " -> " +
                             this.fmt(nState) + " cost=" + newCost +
                             " (via " + this.fmt(curr.state) + ")");
                    updateFrontierDisplay();
                    this.cmd("Step");
                    this.cmd("SetHighlight", this.graphNodes[nb].cId, 0);

                    // Reset cost highlight
                    if (tableRows[nState]) {
                        this.cmd("SetBackgroundColor", tableRows[nState].ids.cost, "#FFFFFF");
                    }
                }
            }
        }

        // --- Path found: trace back and commit reservations ---
        if (pathFound) {
            var path = [];
            var c = pathFound;
            while (c) {
                path.push(c);
                c = parentMap[c];
            }
            path.reverse();

            // Highlight the path in the table (green)
            for (var pi = 0; pi < path.length; pi++) {
                var tr = tableRows[path[pi]];
                if (tr) {
                    this.cmd("SetBackgroundColor", tr.ids.state, "#A5D6A7");
                    this.cmd("SetBackgroundColor", tr.ids.cost, "#A5D6A7");
                    this.cmd("SetBackgroundColor", tr.ids.parent, "#A5D6A7");
                    this.cmd("SetBackgroundColor", tr.ids.known, "#A5D6A7");
                }
            }

            // Highlight physical path
            for (var pi = 0; pi < path.length; pi++) {
                var pZone = path[pi].split(",")[0];
                this.cmd("SetHighlight", this.graphNodes[pZone].cId, 1);
            }

            var pathFormatted = [];
            for (var pi = 0; pi < path.length; pi++) {
                pathFormatted.push(this.fmt(path[pi]));
            }
            this.cmd("SetText", this.msgID, droneName + ": PATH = " + pathFormatted.join(" -> "));
            this.cmd("Step");

            // Un-highlight
            for (var pi = 0; pi < path.length; pi++) {
                var pZone = path[pi].split(",")[0];
                this.cmd("SetHighlight", this.graphNodes[pZone].cId, 0);
            }

            // Commit zone reservations
            for (var pi = 0; pi < path.length; pi++) {
                zoneRes[path[pi]] = (zoneRes[path[pi]] || 0) + 1;
            }
            // Commit edge reservations
            for (var pi = 0; pi < path.length - 1; pi++) {
                var p1 = path[pi].split(",");
                var p2 = path[pi + 1].split(",");
                if (p1[0] !== p2[0]) {
                    var arr = [p1[0], p2[0]].sort();
                    var ek = arr[0] + "-" + arr[1];
                    for (var t = parseInt(p1[1]); t < parseInt(p2[1]); t++) {
                        edgeRes[ek + "," + t] = (edgeRes[ek + "," + t] || 0) + 1;
                    }
                }
            }

            // Update reservations display
            for (var ri = 0; ri < resLabelIDs.length; ri++) {
                this.cmd("Delete", resLabelIDs[ri]);
            }
            resLabelIDs = [];

            var resKeys = Object.keys(zoneRes).sort(function(a, b) {
                var ta = parseInt(a.split(",")[1]);
                var tb = parseInt(b.split(",")[1]);
                return ta - tb;
            });
            for (var ri = 0; ri < resKeys.length; ri++) {
                var rId = this.nextIndex++;
                var y = RES_Y + (ri + 1) * TBL_ROW_H;
                var rParts = resKeys[ri].split(",");
                this.cmd("CreateRectangle", rId,
                         "(" + rParts[0] + ", t=" + rParts[1] + ")  x" + zoneRes[resKeys[ri]],
                         220, TBL_ROW_H, RES_X + 110, y);
                this.cmd("SetBackgroundColor", rId, "#FFF3E0");
                resLabelIDs.push(rId);
                allDynIDs.push(rId);
            }

            this.cmd("SetText", this.msgID, droneName +
                     ": Reservations committed. These slots are now blocked for future drones.");
            this.cmd("Step");
        }

        // --- Clean up table and frontier for next drone ---
        if (d < numDrones) {
            // Delete all table rows
            for (var k in tableRows) {
                var ids = tableRows[k].ids;
                this.cmd("Delete", ids.state);
                this.cmd("Delete", ids.known);
                this.cmd("Delete", ids.cost);
                this.cmd("Delete", ids.parent);
            }
            // Delete frontier display
            for (var fi = 0; fi < fqLabelIDs.length; fi++) {
                this.cmd("Delete", fqLabelIDs[fi]);
            }
            fqLabelIDs = [];

            this.cmd("SetText", this.msgID,
                     "=== Table cleared. Starting fresh Dijkstra for next drone. " +
                     "Reservations persist. ===");
            this.cmd("Step");
        }
    }

    this.cmd("SetText", this.msgID,
             "All " + numDrones + " drones planned successfully! " +
             "Notice how Drone 2 avoided Drone 1's reserved slots.");
    return this.commands;
}
