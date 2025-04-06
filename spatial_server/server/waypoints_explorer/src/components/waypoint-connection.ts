import { Vector3, Quaternion, Euler } from 'three';

AFRAME.registerComponent('waypoint-connection', {
    schema: {
        start: { type: 'vec3', default: { x: 0, y: 0, z: 0 } },
        end: { type: 'vec3', default: { x: 1, y: 1, z: 1 } },
        offset: { type: 'number', default: 0.3 }, // The arrow is shortened by these many meters
        id: { type: 'string' },
    },
    init: function () {
        this.createArrow();
    },
    update: function () {
        this.createArrow();
    },
    createArrow: function () {
        const data = this.data;
        var start = new Vector3(data.start.x, data.start.y, data.start.z);
        var end = new Vector3(data.end.x, data.end.y, data.end.z);
        const direction = new Vector3().subVectors(end, start);
        const length = direction.length();
        direction.normalize();

        // Calculate rotation
        const up = new Vector3(0, 1, 0);
        const quaternion = new Quaternion().setFromUnitVectors(up, direction);
        const rotation = new Euler().setFromQuaternion(quaternion, 'YXZ');

        // Clear previous arrow entities if any
        while (this.el.firstChild) {
            this.el.removeChild(this.el.firstChild);
        }

        // Create the shaft of the arrow
        const shaft = document.createElement('a-cylinder');
        shaft.setAttribute('id', data.id);
        shaft.setAttribute('position', {
            x: (start.x + end.x) / 2,
            y: (start.y + end.y) / 2,
            z: (start.z + end.z) / 2
        });
        shaft.setAttribute('height', length - data.offset);
        shaft.setAttribute('radius', 0.04);
        shaft.object3D.rotation.copy(rotation);
        shaft.setAttribute('color', '#00aaff');

        this.el.appendChild(shaft);
    }
});