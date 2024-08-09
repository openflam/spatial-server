AFRAME.registerComponent('waypoint', {
    schema: {
        name: { type: 'string' },
        radius: { type: 'number', default: 0.1 },
        color: { type: 'string', default: '#00aaff' }
    },

    update: function (oldData: any) {
        let data = this.data;

        // Create a sphere to represent the nav marker
        const sphere = document.createElement('a-sphere');
        sphere.setAttribute('radius', data.radius);
        sphere.setAttribute('color', data.color);
        this.el.appendChild(sphere);

        // Create a text element to display the nav marker name
        const textEntity = document.createElement("a-entity");
        textEntity.setAttribute("text", {
            "width": 2,
            "value": data.name,
            "align": "center",
            "color": data.color
        });
        textEntity.setAttribute("position", { x: 0, y: 0.2, z: 0 });
        textEntity.setAttribute("look-at", "[camera]");
        this.el.appendChild(textEntity);
    }
});
