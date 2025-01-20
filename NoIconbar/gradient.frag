// gradient.frag
precision mediump float;

uniform float time; // Time variable to control animation
uniform vec2 resolution; // Resolution of the screen

void main() {
    vec2 st = gl_FragCoord.xy / resolution.xy;

    // Generate a dynamic gradient color based on the time
    float r = 0.5 + 0.5 * sin(time + st.x * 3.0); // Red color oscillates
    float g = 0.5 + 0.5 * sin(time + st.x * 3.0 + 2.0); // Green color oscillates
    float b = 0.5 + 0.5 * sin(time + st.x * 3.0 + 4.0); // Blue color oscillates

    gl_FragColor = vec4(r, g, b, 1.0);
}
