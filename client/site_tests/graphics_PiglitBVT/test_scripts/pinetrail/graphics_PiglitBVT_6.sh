#!/bin/bash


need_pass=130
failures=0
PIGLIT_PATH=/usr/local/autotest/deps/piglit/piglit/
export PIGLIT_SOURCE_DIR=/usr/local/autotest/deps/piglit/piglit/
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PIGLIT_PATH/lib
export DISPLAY=:0
export XAUTHORITY=/home/chronos/.Xauthority


function run_test()
{
  local name="$1"
  local time="$2"
  local command="$3"
  echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
  echo "+ Running test "$name" of expected runtime $time sec: $command"
  sync
  $command
  if [ $? == 0 ] ; then
    let "need_pass--"
    echo "+ Return code 0 -> Test passed. ($name)"
  else
    let "failures++"
    echo "+ Return code not 0 -> Test failed. ($name)"
  fi
}


pushd $PIGLIT_PATH
run_test "spec/!OpenGL 1.1/fog-modes" 0.0 "bin/fog-modes -auto"
run_test "spec/!OpenGL 1.1/fragment-center" 0.0 "bin/fragment-center -auto"
run_test "spec/!OpenGL 1.1/geterror-inside-begin" 0.0 "bin/geterror-inside-begin -auto"
run_test "spec/!OpenGL 1.1/geterror-invalid-enum" 0.0 "bin/geterror-invalid-enum -auto"
run_test "spec/!OpenGL 1.1/getteximage-formats" 0.0 "bin/getteximage-formats -auto"
run_test "spec/!OpenGL 1.1/getteximage-luminance" 0.0 "bin/getteximage-luminance -auto"
run_test "spec/!OpenGL 1.1/getteximage-simple" 0.0 "bin/getteximage-simple -auto"
run_test "spec/!OpenGL 1.1/getteximage-targets 1D" 0.0 "bin/getteximage-targets 1D -auto -fbo"
run_test "spec/!OpenGL 1.1/getteximage-targets 2D" 0.0 "bin/getteximage-targets 2D -auto -fbo"
run_test "spec/!OpenGL 1.1/hiz" 0.0 "bin/hiz -auto"
run_test "spec/!OpenGL 1.1/incomplete-texture-fixed" 0.0 "bin/incomplete-texture -auto fixed -auto -fbo"
run_test "spec/!OpenGL 1.1/infinite-spot-light" 0.0 "bin/infinite-spot-light -auto"
run_test "spec/!OpenGL 1.1/masked-clear" 0.0 "bin/masked-clear -auto -fbo"
run_test "spec/!OpenGL 1.1/max-texture-size-level" 0.0 "bin/max-texture-size-level -auto -fbo"
run_test "spec/!OpenGL 1.1/polygon-mode" 0.0 "bin/polygon-mode -auto"
run_test "spec/!OpenGL 1.1/proxy-texture" 0.0 "bin/proxy-texture -auto -fbo"
run_test "spec/!OpenGL 1.1/push-pop-texture-state" 0.0 "bin/push-pop-texture-state -auto -fbo"
run_test "spec/!OpenGL 1.1/quad-invariance" 0.0 "bin/quad-invariance -auto -fbo"
run_test "spec/!OpenGL 1.1/r300-readcache" 0.0 "bin/r300-readcache -auto"
run_test "spec/!OpenGL 1.1/read-front" 0.0 "bin/read-front -auto"
run_test "spec/!OpenGL 1.1/readpix-z" 0.0 "bin/readpix-z -auto -fbo"
run_test "spec/!OpenGL 1.1/roundmode-getintegerv" 0.0 "bin/roundmode-getintegerv -auto"
run_test "spec/!OpenGL 1.1/roundmode-pixelstore" 0.0 "bin/roundmode-pixelstore -auto"
run_test "spec/!OpenGL 1.1/scissor-bitmap" 0.0 "bin/scissor-bitmap -auto"
run_test "spec/!OpenGL 1.1/scissor-clear" 0.0 "bin/scissor-clear -auto"
run_test "spec/!OpenGL 1.1/scissor-copypixels" 0.0 "bin/scissor-copypixels -auto"
run_test "spec/!OpenGL 1.1/scissor-depth-clear" 0.0 "bin/scissor-depth-clear -auto"
run_test "spec/!OpenGL 1.1/scissor-many" 0.0 "bin/scissor-many -auto"
run_test "spec/!OpenGL 1.1/scissor-offscreen" 0.0 "bin/scissor-offscreen -auto"
run_test "spec/!OpenGL 1.1/scissor-stencil-clear" 0.0 "bin/scissor-stencil-clear -auto"
run_test "spec/!OpenGL 1.1/sized-texture-format-channels" 0.0 "bin/sized-texture-format-channels -auto -fbo"
run_test "spec/!OpenGL 1.1/stencil-drawpixels" 0.0 "bin/stencil-drawpixels -auto"
run_test "spec/!OpenGL 1.1/texgen" 0.0 "bin/texgen -auto"
run_test "spec/!OpenGL 1.1/texredefine" 0.0 "bin/texredefine -auto"
run_test "spec/!OpenGL 1.1/texsubimage" 0.0 "bin/texsubimage -auto"
run_test "spec/!OpenGL 1.1/texture-al" 0.0 "bin/texture-al -auto"
run_test "spec/!OpenGL 1.1/texwrap 1D" 0.0 "bin/texwrap -fbo -auto 1D GL_RGBA8"
run_test "spec/!OpenGL 1.1/texwrap 1D proj" 0.0 "bin/texwrap -fbo -auto 1D GL_RGBA8 proj"
run_test "spec/!OpenGL 1.1/texwrap 2D" 0.0 "bin/texwrap -fbo -auto 2D GL_RGBA8"
run_test "spec/!OpenGL 1.1/texwrap 2D proj" 0.0 "bin/texwrap -fbo -auto 2D GL_RGBA8 proj"
run_test "spec/!OpenGL 1.1/texwrap formats" 0.0 "bin/texwrap -fbo -auto"
run_test "spec/!OpenGL 1.1/tri-tex-crash" 0.0 "bin/tri-tex-crash -auto"
run_test "spec/!OpenGL 1.1/triangle-guardband-viewport" 0.0 "bin/triangle-guardband-viewport -auto -fbo"
run_test "spec/!OpenGL 1.1/two-sided-lighting" 0.0 "bin/two-sided-lighting -auto"
run_test "spec/!OpenGL 1.1/user-clip" 0.0 "bin/user-clip -auto"
run_test "spec/!OpenGL 1.1/varray-disabled" 0.0 "bin/varray-disabled -auto"
run_test "spec/!OpenGL 1.1/vbo-buffer-unmap" 0.0 "bin/vbo-buffer-unmap -auto"
run_test "spec/!OpenGL 1.1/windowoverlap" 0.0 "bin/windowoverlap -auto"
run_test "spec/!OpenGL 1.2/copyteximage 3D" 0.0 "bin/copyteximage -auto 3D"
run_test "spec/!OpenGL 1.2/crash-texparameter-before-teximage" 0.0 "bin/crash-texparameter-before-teximage -auto"
run_test "spec/!OpenGL 1.2/draw-elements-vs-inputs" 0.0 "bin/draw-elements-vs-inputs -auto"
run_test "spec/!OpenGL 1.2/getteximage-targets 3D" 0.0 "bin/getteximage-targets 3D -auto -fbo"
run_test "spec/!OpenGL 1.2/lodclamp" 0.0 "bin/lodclamp -auto"
run_test "spec/!OpenGL 1.2/lodclamp-between" 0.0 "bin/lodclamp-between -auto"
run_test "spec/!OpenGL 1.2/lodclamp-between-max" 0.0 "bin/lodclamp-between-max -auto"
run_test "spec/!OpenGL 1.2/mipmap-setup" 0.0 "bin/mipmap-setup -auto"
run_test "spec/!OpenGL 1.2/tex-skipped-unit" 0.0 "bin/tex-skipped-unit -auto"
run_test "spec/!OpenGL 1.2/teximage-errors" 0.0 "bin/teximage-errors -auto"
run_test "spec/!OpenGL 1.2/texture-packed-formats" 0.0 "bin/texture-packed-formats -auto"
run_test "spec/!OpenGL 1.2/two-sided-lighting-separate-specular" 0.0 "bin/two-sided-lighting-separate-specular -auto"
run_test "spec/!OpenGL 1.3/tex-border-1" 0.0 "bin/tex-border-1 -auto"
run_test "spec/!OpenGL 1.3/tex3d-depth1" 0.0 "bin/tex3d-depth1 -auto -fbo"
run_test "spec/!OpenGL 1.3/texunits" 0.0 "bin/texunits -auto"
run_test "spec/!OpenGL 1.4/blendminmax" 0.0 "bin/blendminmax -auto"
run_test "spec/!OpenGL 1.4/blendsquare" 0.0 "bin/blendsquare -auto"
run_test "spec/!OpenGL 1.4/draw-batch" 0.0 "bin/draw-batch -auto"
run_test "spec/!OpenGL 1.4/fdo25614-genmipmap" 0.0 "bin/fdo25614-genmipmap -auto"
run_test "spec/!OpenGL 1.4/stencil-wrap" 0.0 "bin/stencil-wrap -auto"
run_test "spec/!OpenGL 1.4/tex1d-2dborder" 0.0 "bin/tex1d-2dborder -auto"
run_test "spec/!OpenGL 1.4/triangle-rasterization-overdraw" 0.0 "bin/triangle-rasterization-overdraw -auto"
run_test "spec/!OpenGL 1.5/draw-elements" 0.0 "bin/draw-elements -auto"
run_test "spec/!OpenGL 1.5/draw-elements-user" 0.0 "bin/draw-elements -auto user"
run_test "spec/!OpenGL 1.5/draw-vertices" 0.0 "bin/draw-vertices -auto"
run_test "spec/!OpenGL 1.5/draw-vertices-user" 0.0 "bin/draw-vertices -auto user"
run_test "spec/!OpenGL 1.5/isbufferobj" 0.0 "bin/isbufferobj -auto"
run_test "spec/!OpenGL 2.0/attribs" 0.0 "bin/attribs -auto -fbo"
run_test "spec/!OpenGL 2.0/clear-varray-2.0" 0.0 "bin/clear-varray-2.0 -auto"
run_test "spec/!OpenGL 2.0/clip-flag-behavior" 0.0 "bin/clip-flag-behavior -auto"
run_test "spec/!OpenGL 2.0/depth-tex-modes-glsl" 0.0 "bin/depth-tex-modes-glsl -auto"
run_test "spec/!OpenGL 2.0/early-z" 0.0 "bin/early-z -auto"
run_test "spec/!OpenGL 2.0/fragment-and-vertex-texturing" 0.0 "bin/fragment-and-vertex-texturing -auto"
run_test "spec/!OpenGL 2.0/getattriblocation-conventional" 0.0 "bin/getattriblocation-conventional -auto"
run_test "spec/!OpenGL 2.0/incomplete-texture-glsl" 0.0 "bin/incomplete-texture -auto glsl -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side" 0.0 "bin/vertex-program-two-side -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side back" 0.0 "bin/vertex-program-two-side back -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side back back2" 0.0 "bin/vertex-program-two-side back back2 -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side back2" 0.0 "bin/vertex-program-two-side back2 -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side enabled" 0.0 "bin/vertex-program-two-side enabled -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side enabled front" 0.0 "bin/vertex-program-two-side enabled front -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side enabled front back" 0.0 "bin/vertex-program-two-side enabled front back -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side front" 0.0 "bin/vertex-program-two-side front -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side front back" 0.0 "bin/vertex-program-two-side front back -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side front back back2" 0.0 "bin/vertex-program-two-side front back back2 -auto -fbo"
run_test "spec/!OpenGL 2.0/vertex-program-two-side front back2" 0.0 "bin/vertex-program-two-side front back2 -auto -fbo"
run_test "spec/!OpenGL 2.0/vs-point_size-zero" 0.0 "bin/vs-point_size-zero -auto"
run_test "spec/!OpenGL 2.1/minmax" 0.0 "bin/gl-2.1-minmax -auto -fbo"
run_test "spec/!OpenGL 3.0/genmipmap-errors" 0.0 "bin/genmipmap-errors -auto -fbo"
run_test "spec/3DFX_texture_compression_FXT1/invalid formats" 0.0 "bin/arb_texture_compression-invalid-formats fxt1"
run_test "spec/AMD_shader_stencil_export/arb-undefined.frag" 0.0 "bin/glslparsertest tests/spec/amd_shader_stencil_export/arb-undefined.frag fail 1.20"
run_test "spec/APPLE_vertex_array_object/isvertexarray" 0.0 "bin/arb_vertex_array-isvertexarray apple -auto -fbo"
run_test "spec/APPLE_vertex_array_object/vao-01" 0.0 "bin/vao-01 -auto"
run_test "spec/APPLE_vertex_array_object/vao-02" 0.0 "bin/vao-02 -auto"
run_test "spec/ARB_ES2_compatibility/arb_es2_compatibility-depthrangef" 0.0 "bin/arb_es2_compatibility-depthrangef -auto"
run_test "spec/ARB_ES2_compatibility/arb_es2_compatibility-getshaderprecisionformat" 0.0 "bin/arb_es2_compatibility-getshaderprecisionformat -auto"
run_test "spec/ARB_ES2_compatibility/arb_es2_compatibility-maxvectors" 0.0 "bin/arb_es2_compatibility-maxvectors -auto"
run_test "spec/ARB_ES2_compatibility/arb_es2_compatibility-releaseshadercompiler" 0.0 "bin/arb_es2_compatibility-releaseshadercompiler -auto"
run_test "spec/ARB_ES2_compatibility/arb_es2_compatibility-shadercompiler" 0.0 "bin/arb_es2_compatibility-shadercompiler -auto"
run_test "spec/ARB_ES2_compatibility/fbo-alphatest-formats" 0.0 "bin/fbo-alphatest-formats -auto GL_ARB_ES2_compatibility"
run_test "spec/ARB_ES2_compatibility/fbo-blending-formats" 0.0 "bin/fbo-blending-formats -auto GL_ARB_ES2_compatibility"
run_test "spec/ARB_ES2_compatibility/fbo-clear-formats" 0.0 "bin/fbo-clear-formats -auto GL_ARB_ES2_compatibility"
run_test "spec/ARB_ES2_compatibility/fbo-colormask-formats" 0.0 "bin/fbo-colormask-formats -auto GL_ARB_ES2_compatibility"
run_test "spec/ARB_ES2_compatibility/fbo-missing-attachment-clear" 0.0 "bin/fbo-missing-attachment-clear -auto"
run_test "spec/ARB_ES2_compatibility/get-renderbuffer-internalformat" 0.0 "bin/get-renderbuffer-internalformat GL_ARB_ES2_compatibility -auto -fbo"
run_test "spec/ARB_ES2_compatibility/texwrap formats" 0.0 "bin/texwrap -fbo -auto GL_ARB_ES2_compatibility"
run_test "spec/ARB_color_buffer_float/GL_RGBA8-render-sanity" 0.0 "bin/arb_color_buffer_float-render GL_RGBA8 sanity "
run_test "spec/ARB_color_buffer_float/GL_RGBA8-render-sanity-fog" 0.0 "bin/arb_color_buffer_float-render GL_RGBA8 sanity fog"
run_test "spec/ARB_copy_buffer/copy_buffer_coherency" 0.0 "bin/copy_buffer_coherency -auto"
run_test "spec/ARB_copy_buffer/copybuffersubdata" 0.0 "bin/copybuffersubdata -auto"
run_test "spec/ARB_copy_buffer/dlist" 0.0 "bin/arb_copy_buffer-dlist -auto -fbo"
run_test "spec/ARB_copy_buffer/get" 0.0 "bin/arb_copy_buffer-get -auto -fbo"
run_test "spec/ARB_copy_buffer/negative-bound-zero" 0.0 "bin/arb_copy_buffer-negative-bound-zero -auto -fbo"
run_test "spec/ARB_copy_buffer/negative-bounds" 0.0 "bin/arb_copy_buffer-negative-bounds -auto -fbo"
run_test "spec/ARB_copy_buffer/negative-mapped" 0.0 "bin/arb_copy_buffer-negative-mapped -auto -fbo"
run_test "spec/ARB_copy_buffer/overlap" 0.0 "bin/arb_copy_buffer-overlap -auto -fbo"
run_test "spec/ARB_copy_buffer/targets" 0.0 "bin/arb_copy_buffer-targets -auto -fbo"
run_test "spec/ARB_depth_texture/depth-tex-modes" 0.0 "bin/depth-tex-modes -auto"
run_test "spec/ARB_depth_texture/fbo-depth-GL_DEPTH_COMPONENT16-clear" 0.0 "bin/fbo-depth -auto clear GL_DEPTH_COMPONENT16"
run_test "spec/ARB_depth_texture/fbo-depth-GL_DEPTH_COMPONENT16-readpixels" 0.0 "bin/fbo-depth -auto readpixels GL_DEPTH_COMPONENT16"
run_test "spec/ARB_depth_texture/fbo-depth-GL_DEPTH_COMPONENT16-tex1d" 0.0 "bin/fbo-depth-tex1d -auto GL_DEPTH_COMPONENT16"
run_test "spec/ARB_depth_texture/fbo-depth-GL_DEPTH_COMPONENT24-clear" 0.0 "bin/fbo-depth -auto clear GL_DEPTH_COMPONENT24"
popd

if [ $need_pass == 0 ] ; then
  echo "+---------------------------------------------+"
  echo "| Overall pass, as all 130 tests have passed. |"
  echo "+---------------------------------------------+"
else
  echo "+-----------------------------------------------------------+"
  echo "| Overall failure, as $need_pass tests did not pass and $failures failed. |"
  echo "+-----------------------------------------------------------+"
fi
exit $need_pass

