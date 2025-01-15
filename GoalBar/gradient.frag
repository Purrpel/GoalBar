ECHO is on.
#ifdef GL_ES
precision mediump float;
#endif

uniform float time;
uniform vec2 resolution;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    float color = 0.5 + 0.5 * sin(time + uv.x * 3.1416);
    gl_FragColor = vec4(uv.x, uv.y, color, 1.0);
}
