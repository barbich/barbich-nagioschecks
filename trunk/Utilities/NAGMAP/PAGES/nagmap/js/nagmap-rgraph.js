var Log = {
	elem: false,
	getElem: function() {
		return this.elem? this.elem : this.elem = $('log');
	},

	write: function(text) {
		var elem = this.getElem();
		elem.set('html', text);
	}
};

function init() {
  //Set node radius to 3 pixels.
  Config.nodeRadius = 3;

  //Create a canvas object.
  var canvas= new Canvas('infovis', '#ccddee', '#772277');

  //Instanciate the RGraph
  var rgraph= new RGraph(canvas,  {
	//Here will be stored the
	//clicked node name and id
  	nodeId: "",
  	nodeName: "",

  	//Refresh the clicked node name
	//and id values before computing
	//an animation.
	onBeforeCompute: function(node) {
  		Log.write("centering " + node.name + "...");
		this.nodeId = node.id;
  		this.nodeName = node.name;
  	},

  //Add a controller to assign the node's name
  //and some extra events to the created label.
  	onCreateLabel: function(domElement, node) {
  		var d = $(domElement);
  		d.setOpacity(0.6).set('html', node.name).addEvents({
  			'mouseenter': function() {
  				d.setOpacity(1);
  			},
  			'mouseleave': function() {
  				d.setOpacity(0.6);
  			},
  			'click': function() {
				if(Log.elem.innerHTML == "done") rgraph.onClick(d.id);
  			}
  		});
  	},

	//Once the label is placed we slightly
	//change the positioning values in order
	//to center or hide the label
  	onPlaceLabel: function(domElement, node) {
		var d = $(domElement);
		d.setStyle('display', 'none');
		 if(node._depth <= 1) {
			d.set('html', node.name).setStyles({
				'width': '',
				'height': '',
				'display':''
			}).setStyle('left', (d.getStyle('left').toInt()
				- domElement.offsetWidth / 2) + 'px');
		}
	},

	//Once the node is centered we
	//can request for the new dependency
	//graph.
	onAfterCompute: function() {
		Log.write("done");
//		this.requestGraph();
	},

	//We make our call to the service in order
	//to fetch the new dependency tree for
	//this package.
/*
   	requestGraph: function() {
  		var that = this, id = this.nodeId, name = this.nodeName;
  		Log.write("requesting info...");
  		var jsonRequest = new Request.JSON({
  			'url': '/dnagmap/tree/',
//  			'url': '/dnagmap/tree/'
//					+ encodeURIComponent(name) + '/',

  			onSuccess: function(json) {
  				Log.write("morphing...");
				//Once me received the data
				//we preprocess the ids of the nodes
				//received to match existing nodes
				//in the graph and perform a morphing
				//operation.
  				that.preprocessTree(json);
				GraphOp.morph(rgraph, json, {
  					'id': id,
  					'type': 'fade',
  					'duration':2000,
  					hideLabels:true,
  					onComplete: function() {
						Log.write('done');
					},
  					onAfterCompute: $empty,
  					onBeforeCompute: $empty
  				});
  			},

  			onFailure: function() {
  				Log.write("sorry, the request failed");
  			}
  		}).get();
  	},
*/
	//This method searches for nodes that already
	//existed in the visualization and sets the new node's
	//id to the previous one. That way, all existing nodes
	//that exist also in the new data won't be deleted.
 	preprocessTree: function(json) {
  		var ch = json.children;
  		var getNode = function(nodeName) {
  			for(var i=0; i<ch.length; i++) {
  				if(ch[i].name == nodeName) return ch[i];
  			}
  			return false;
  		};
  		json.id = rgraph.root;
		var root = rgraph.graph.getNode(rgraph.root);
  		GraphUtil.eachAdjacency(root, function(elem) {
  			var nodeTo = elem.nodeTo, jsonNode = getNode(nodeTo.name);
  			if(jsonNode) jsonNode.id = nodeTo.id;
  		});
  	}

  });

  return rgraph;
}

/*
window.addEvent('domready', function() {
	var rgraph = init();
	new Request.JSON({
	  	'url':'/dnagmap/tree/',
	  	onSuccess: function(json) {
			  //load wine dependency tree.
			 rgraph.loadTreeFromJSON(json);
			  //compute positions
			  rgraph.compute();
			  //make first plot
			  rgraph.plot();
			  Log.write("done");
			  rgraph.controller.nodeName = name;
	  	},

	  	onFailure: function() {
	  		Log.write("failed!");
	  	}
	}).get();
*/

function initrunTree() {
    Log.write("Initrun done");
    window.addEvent('domready', function() {
	var rgraph = init();
	new Request.JSON({
	  	'url':'/dnagmap/tree/',
	  	onSuccess: function(json) {
			  //load wine dependency tree.
			 rgraph.loadTreeFromJSON(json);
			  //compute positions
			  rgraph.compute();
			  //make first plot
			  rgraph.plot();
			  Log.write("done");
			  rgraph.controller.nodeName = name;
	  	},
	  	onFailure: function() {
	  		Log.write("failed!");
	  	}
    	    }).get();
    });
}

function initrunGraph() {
    Log.write("Initrun done");
    window.addEvent('domready', function() {
	var rgraph = init();
	new Request.JSON({
	  	'url':'/dnagmap/tree/',
	  	onSuccess: function(json) {
			  //load wine dependency tree.
			 rgraph.loadGraphFromJSON(json);
			  //compute positions
			  rgraph.compute();
			  //make first plot
			  rgraph.plot();
			  Log.write("done");
			  rgraph.controller.nodeName = name;
	  	},
	  	onFailure: function() {
	  		Log.write("failed!");
	  	}
    	    }).get();
    });
}
