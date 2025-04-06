const path = require('path');

module.exports = {
    entry: './src/register-components.ts',
    mode: 'production',
    module: {
        rules: [
            {
                test: /\.tsx?$/,
                use: 'ts-loader',
                exclude: /node_modules/,
            },
        ],
    },
    resolve: {
        extensions: ['.tsx', '.ts', '.js'],
    },
    output: {
        filename: 'register-components.js',
        path: path.resolve(__dirname, '../static/scripts/waypoints_explorer'),
        library: 'waypointsExplorer',
    }
};