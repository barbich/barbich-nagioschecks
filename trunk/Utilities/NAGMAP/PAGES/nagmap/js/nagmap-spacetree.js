var Infovis = {
	initLayout: function() {
		var size = Window.getSize();
		var header = $('header'), left = $('left'), infovisContainer = $('infovis');
		var headerOffset = header.getSize().y, leftOffset = left.getSize().x;

		var newStyles = {
			'height': Math.floor((size.y - headerOffset) / 1),
			'width' : Math.floor((size.x - leftOffset) / 1)
		};

		infovisContainer.setProperties(newStyles);
		infovisContainer.setStyles(newStyles);
		infovisContainer.setStyles({
			'position':'absolute',
			'top': headerOffset + 'px',
			'left': leftOffset + 'px'
		});
		left.setStyle('height', newStyles.height);
	}
};

var Log = {
	elem: $('log'),
	write: function(text) {
		if(!this.elem) this.elem = $('log');
		this.elem.set('html', text);
	}
};

function init() {
	//computes page layout (not a library function, used to adjust some css thingys on the page)
//	Infovis.initLayout();
	//Create random generated tree.
	  //var json= Feeder.makeTree();
          
	  //Create a new canvas instance.
	  var canvas= new Canvas('infovis');
          var nagiosdetails=$('nagios-details');
	  //Create a new ST instance
	  st= new ST(canvas, {
		onBeforeCompute: function(node) {
				Log.write("loading " + node.name);
                                nagiosdetails.innerHTML="Node name: " +node.name;
		},
		
		onAfterCompute: function() {
			Log.write("done");
		},
                onCreateLabel: function(domElement, node) {
                    var d=$(domElement);
                    d.set('tween', { duration: 300 }).set('html', node.name).setOpacity(0.7).setStyle('background-color',node.data[1].value).addEvents({
//                    d.set('tween', { duration: 300 }).set('html', node.name).setOpacity(0.4).addEvents({
                        'mouseenter': function() {
                            d.tween('opacity', 1);
                        },
                        'mouseleave': function() {
                            d.tween('opacity', 0.7);
                        }
                    })
                },
//                request: function(node,level,onComplete) {
//			Log.write("done");
//    				nagiosdetails.innerHTML="Node name: " ;
//                        onComplete.onComplete
//                },
//		request: function(nodeId, level, onComplete) {
//			Feeder.request(nodeId, level, onComplete);
//		}
	  });
	  //load json data
	  //st.loadFromJSON(json);
	  //compute node positions and layout
	  //st.compute();
	  //optional: make a translation of the tree
//	  Tree.Geometry.translate(st.tree, new Complex(-200, 0), "startPos");
	  //Emulate a click on the root node.
//	  st.onClick(st.tree.id);
	  
	  //Add click handler to switch spacetree orientation.
	  var checkbox = document.getElementById('switch');
	  checkbox.onclick = function () {
	  	st.switchPosition({
	  		onComplete: function() {}
	  	});
	  };
          return st;
}

function initrunTree() {
    Log.write("Initrun done");
    Infovis.initLayout();
    window.addEvent('domready', function() {
        Log.write("domready");
        var rgraph = init();

        new Request.JSON({
                'url':'/dnagmap/stree/sancho/',
                onSuccess: function(json) {
                          //load wine dependency tree.
                         rgraph.loadFromJSON(json);
                          //compute positions
                          rgraph.compute();
//                          Tree.Geometry.translate(st.tree, new Complex(-200, 0), "startPos");
                          st.onClick(st.tree.id);
//                        st.onClick(
//			Log.write("done"););
//    				nagiosdetails.innerHTML="Node name: " ;
//                        onComplete.onComplete
//                },
                          //make first plot
//                          rgraph.plot();
                          Log.write("done");
//                          rgraph.controller.nodeName = name;
                },
                onFailure: function() {
                        Log.write("failed!");
                }
            }).get();

      });    
      
}

