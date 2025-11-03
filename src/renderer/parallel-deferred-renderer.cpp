#include <omp.h>

#include "shader.h"
#include "camera.h"
#include "model.h"
#include "shape.h"
#include "texture.h"
#include "light.h"
#include "skybox.h"
#include "material.h"

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>
#include <imgui.h>
#include <imgui_impl_glfw_gl3.h>

#include <string>
#include <fstream>
#include <sstream>
#include <map>
#include <vector>
#include <tuple>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <random>


//---------------
// GLFW Callbacks
//---------------

static void error_callback(int error, const char* description);
void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode);
void mouse_callback(GLFWwindow* window, double xpos, double ypos);
void mouse_button_callback(GLFWwindow* window, int button, int action, int mods);
void scroll_callback(GLFWwindow* window, double xoffset, double yoffset);

//---------------------
// Functions prototypes
//---------------------

void cameraMove();
void imGuiSetup();
void gBufferSetup();
void saoSetup();
void postprocessSetup();
void iblSetup();

//---------------------------------
// Variables & objects declarations
//---------------------------------

GLuint WIDTH = 1280;
GLuint HEIGHT = 720;

GLuint screenQuadVAO, screenQuadVBO;
GLuint gBuffer, zBuffer, gPosition, gNormal, gAlbedo, gEffects;
GLuint saoFBO, saoBlurFBO, saoBuffer, saoBlurBuffer;
GLuint postprocessFBO, postprocessBuffer;
GLuint envToCubeFBO, irradianceFBO, prefilterFBO, brdfLUTFBO, envToCubeRBO, irradianceRBO, prefilterRBO, brdfLUTRBO;

GLint gBufferView = 1;
GLint tonemappingMode = 1;
GLint lightDebugMode = 3;
GLint attenuationMode = 2;
GLint saoSamples = 12;
GLint saoTurns = 7;
GLint saoBlurSize = 4;
GLint motionBlurMaxSamples = 32;

GLfloat lastX = WIDTH / 2;
GLfloat lastY = HEIGHT / 2;
GLfloat deltaTime = 0.0f;
GLfloat lastFrame = 0.0f;
GLfloat deltaGeometryTime = 0.0f;
GLfloat deltaLightingTime = 0.0f;
GLfloat deltaSAOTime = 0.0f;
GLfloat deltaPostprocessTime = 0.0f;
GLfloat deltaForwardTime = 0.0f;
GLfloat deltaGUITime = 0.0f;
GLfloat materialRoughness = 0.01f;
GLfloat materialMetallicity = 0.02f;
GLfloat ambientIntensity = 0.005f;
GLfloat saoRadius = 0.3f;
GLfloat saoBias = 0.001f;
GLfloat saoScale = 0.7f;
GLfloat saoContrast = 0.8f;
GLfloat lightPointRadius1 = 3.0f;
GLfloat lightPointRadius2 = 3.0f;
GLfloat lightPointRadius3 = 3.0f;
GLfloat cameraAperture = 16.0f;
GLfloat cameraShutterSpeed = 0.5f;
GLfloat cameraISO = 1000.0f;
GLfloat modelRotationSpeed = 0.0f;

bool cameraMode;
bool pointMode = false;
bool directionalMode = false;
bool iblMode = true;
bool saoMode = false;
bool fxaaMode = false;
bool motionBlurMode = false;
bool screenMode = false;
bool firstMouse = true;
bool guiIsOpen = true;
bool keys[1024];

glm::vec3 albedoColor = glm::vec3(1.0f);
glm::vec3 materialF0 = glm::vec3(0.04f);  // UE4 dielectric
glm::vec3 lightPointPosition1 = glm::vec3(1.5f, 0.75f, 1.0f);
glm::vec3 lightPointPosition2 = glm::vec3(-1.5f, 1.0f, 1.0f);
glm::vec3 lightPointPosition3 = glm::vec3(0.0f, 0.75f, -1.2f);
glm::vec3 lightPointColor1 = glm::vec3(1.0f);
glm::vec3 lightPointColor2 = glm::vec3(1.0f);
glm::vec3 lightPointColor3 = glm::vec3(1.0f);
glm::vec3 lightDirectionalDirection1 = glm::vec3(-0.2f, -1.0f, -0.3f);
glm::vec3 lightDirectionalColor1 = glm::vec3(1.0f);
glm::vec3 modelPosition = glm::vec3(0.0f);
glm::vec3 modelRotationAxis = glm::vec3(0.0f, 1.0f, 0.0f);
glm::vec3 modelScale = glm::vec3(0.1f);

glm::mat4 projViewModel;
glm::mat4 prevProjViewModel = projViewModel;
glm::mat4 envMapProjection = glm::perspective(glm::radians(90.0f), 1.0f, 0.1f, 10.0f);
glm::mat4 envMapView[] =
{
    glm::lookAt(glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
    glm::lookAt(glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(-1.0f,  0.0f,  0.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
    glm::lookAt(glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(0.0f,  1.0f,  0.0f), glm::vec3(0.0f,  0.0f,  1.0f)),
    glm::lookAt(glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(0.0f, -1.0f,  0.0f), glm::vec3(0.0f,  0.0f, -1.0f)),
    glm::lookAt(glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(0.0f,  0.0f,  1.0f), glm::vec3(0.0f, -1.0f,  0.0f)),
    glm::lookAt(glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(0.0f,  0.0f, -1.0f), glm::vec3(0.0f, -1.0f,  0.0f))
};

Camera camera(glm::vec3(0.0f, 0.0f, 4.0f));

Shader gBufferShader;
Shader latlongToCubeShader;
Shader simpleShader;
Shader lightingBRDFShader;
Shader irradianceIBLShader;
Shader prefilterIBLShader;
Shader integrateIBLShader;
Shader firstpassPPShader;
Shader saoShader;
Shader saoBlurShader;

Texture objectAlbedo;
Texture objectNormal;
Texture objectRoughness;
Texture objectMetalness;
Texture objectAO;
Texture envMapHDR;
Texture envMapCube;
Texture envMapIrradiance;
Texture envMapPrefilter;
Texture envMapLUT;

Material pbrMat;

Model objectModel;

Light lightPoint1;
Light lightPoint2;
Light lightPoint3;
Light lightDirectional1;

Shape quadRender;
Shape envCubeRender;


int main(int argc, char* argv[])
{
    std::cout << "Running with " << omp_get_max_threads() << " threads\n";
    glfwInit();

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 0);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_RESIZABLE, GL_FALSE);

    GLFWmonitor* glfwMonitor = glfwGetPrimaryMonitor();
    const GLFWvidmode* glfwMode = glfwGetVideoMode(glfwMonitor);

    glfwWindowHint(GLFW_RED_BITS, glfwMode->redBits);
    glfwWindowHint(GLFW_GREEN_BITS, glfwMode->greenBits);
    glfwWindowHint(GLFW_BLUE_BITS, glfwMode->blueBits);
    glfwWindowHint(GLFW_REFRESH_RATE, glfwMode->refreshRate);

    WIDTH = glfwMode->width;
    HEIGHT = glfwMode->height;

    GLFWwindow* window = glfwCreateWindow(WIDTH, HEIGHT, "Parallel-Deferred-Renderer", glfwMonitor, NULL);
    //    GLFWwindow* window = glfwCreateWindow(WIDTH, HEIGHT, "Parallel-Deferred-Renderer", nullptr, nullptr);
    glfwMakeContextCurrent(window);

    glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
    glfwSwapInterval(1);

    gladLoadGL();

    glViewport(0, 0, WIDTH, HEIGHT);

    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LESS);
    glEnable(GL_TEXTURE_CUBE_MAP_SEAMLESS);

    ImGui_ImplGlfwGL3_Init(window, true);
    glfwSetKeyCallback(window, key_callback);
    glfwSetCursorPosCallback(window, mouse_callback);
    glfwSetMouseButtonCallback(window, mouse_button_callback);
    glfwSetScrollCallback(window, scroll_callback);


    //----------
    // Shader(s)
    //----------
    gBufferShader.setShader("resources/shaders/gBuffer.vert", "resources/shaders/gBuffer.frag");
    latlongToCubeShader.setShader("resources/shaders/latlongToCube.vert", "resources/shaders/latlongToCube.frag");

    simpleShader.setShader("resources/shaders/lighting/simple.vert", "resources/shaders/lighting/simple.frag");
    lightingBRDFShader.setShader("resources/shaders/lighting/lightingBRDF.vert", "resources/shaders/lighting/lightingBRDF.frag");
    irradianceIBLShader.setShader("resources/shaders/lighting/irradianceIBL.vert", "resources/shaders/lighting/irradianceIBL.frag");
    prefilterIBLShader.setShader("resources/shaders/lighting/prefilterIBL.vert", "resources/shaders/lighting/prefilterIBL.frag");
    integrateIBLShader.setShader("resources/shaders/lighting/integrateIBL.vert", "resources/shaders/lighting/integrateIBL.frag");

    firstpassPPShader.setShader("resources/shaders/postprocess/postprocess.vert", "resources/shaders/postprocess/firstpass.frag");
    saoShader.setShader("resources/shaders/postprocess/sao.vert", "resources/shaders/postprocess/sao.frag");
    saoBlurShader.setShader("resources/shaders/postprocess/sao.vert", "resources/shaders/postprocess/saoBlur.frag");


    //-----------
    // Textures(s)
    //-----------
    objectAlbedo.setTexture("resources/textures/pbr/rustediron/rustediron_albedo.png", "ironAlbedo", true);
    objectNormal.setTexture("resources/textures/pbr/rustediron/rustediron_normal.png", "ironNormal", true);
    objectRoughness.setTexture("resources/textures/pbr/rustediron/rustediron_roughness.png", "ironRoughness", true);
    objectMetalness.setTexture("resources/textures/pbr/rustediron/rustediron_metalness.png", "ironMetalness", true);
    objectAO.setTexture("resources/textures/pbr/rustediron/rustediron_ao.png", "ironAO", true);

    envMapHDR.setTextureHDR("resources/textures/hdr/appart.hdr", "appartHDR", true);

    envMapCube.setTextureCube(512, GL_RGB, GL_RGB16F, GL_FLOAT, GL_LINEAR_MIPMAP_LINEAR);
    envMapIrradiance.setTextureCube(32, GL_RGB, GL_RGB16F, GL_FLOAT, GL_LINEAR);
    envMapPrefilter.setTextureCube(128, GL_RGB, GL_RGB16F, GL_FLOAT, GL_LINEAR_MIPMAP_LINEAR);
    envMapPrefilter.computeTexMipmap();
    envMapLUT.setTextureHDR(512, 512, GL_RG, GL_RG16F, GL_FLOAT, GL_LINEAR);


    //-----------
    // Material(s)
    //-----------
    //    pbrMat.setShader(gBufferShader);
    //    pbrMat.addTexture("texAlbedo", ironAlbedo);
    //    pbrMat.addTexture("texNormal", ironNormal);
    //    pbrMat.addTexture("texRoughness", ironRoughness);
    //    pbrMat.addTexture("texMetalness", ironMetalness);
    //    pbrMat.addTexture("texAO", ironAO);
    //    pbrMat.addTexture("texAlbedo", TextureObject ("resources/textures/pbr/rustediron/rustediron_albedo.png", "ironAlbedo", true));
    //    pbrMat.addTexture("texNormal", TextureObject ("resources/textures/pbr/rustediron/rustediron_normal.png", "ironNormal", true));
    //    pbrMat.addTexture("texRoughness", TextureObject ("resources/textures/pbr/rustediron/rustediron_roughness.png", "ironRoughness", true));
    //    pbrMat.addTexture("texMetalness", TextureObject ("resources/textures/pbr/rustediron/rustediron_metalness.png", "ironMetalness", true));
    //    pbrMat.addTexture("texAO", TextureObject ("resources/textures/pbr/rustediron/rustediron_ao.png", "ironAO", true));


    //---------
    // Model(s)
    //---------
    objectModel.loadModel("resources/models/shaderball/shaderball.obj");


    //---------------
    // Shape(s)
    //---------------
    envCubeRender.setShape("cube", glm::vec3(0.0f));
    quadRender.setShape("quad", glm::vec3(0.0f));


    //----------------
    // Light source(s)
    //----------------
    lightPoint1.setLight(lightPointPosition1, glm::vec4(lightPointColor1, 1.0f), lightPointRadius1, true);
    lightPoint2.setLight(lightPointPosition2, glm::vec4(lightPointColor2, 1.0f), lightPointRadius2, true);
    lightPoint3.setLight(lightPointPosition3, glm::vec4(lightPointColor3, 1.0f), lightPointRadius3, true);

    lightDirectional1.setLight(lightDirectionalDirection1, glm::vec4(lightDirectionalColor1, 1.0f));


    //-------
    // Skybox
    //-------


    //---------------------------------------------------------
    // Set the samplers for the lighting/post-processing passes
    //---------------------------------------------------------
    lightingBRDFShader.useShader();
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "gPosition"), 0);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "gAlbedo"), 1);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "gNormal"), 2);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "gEffects"), 3);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "sao"), 4);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "envMap"), 5);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "envMapIrradiance"), 6);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "envMapPrefilter"), 7);
    glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "envMapLUT"), 8);

    saoShader.useShader();
    glUniform1i(glGetUniformLocation(saoShader.Program, "gPosition"), 0);
    glUniform1i(glGetUniformLocation(saoShader.Program, "gNormal"), 1);

    firstpassPPShader.useShader();
    glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "sao"), 1);
    glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "gEffects"), 2);

    latlongToCubeShader.useShader();
    glUniform1i(glGetUniformLocation(latlongToCubeShader.Program, "envMap"), 0);

    irradianceIBLShader.useShader();
    glUniform1i(glGetUniformLocation(irradianceIBLShader.Program, "envMap"), 0);

    prefilterIBLShader.useShader();
    glUniform1i(glGetUniformLocation(prefilterIBLShader.Program, "envMap"), 0);


    //---------------
    // G-Buffer setup
    //---------------
    gBufferSetup();


    //------------
    // SAO setup
    //------------
    saoSetup();


    //---------------------
    // Postprocessing setup
    //---------------------
    postprocessSetup();


    //----------
    // IBL setup
    //----------
    iblSetup();


    //------------------------------
    // Queries setting for profiling
    //------------------------------
    GLuint64 startGeometryTime, startLightingTime, startSAOTime, startPostprocessTime, startForwardTime, startGUITime;
    GLuint64 stopGeometryTime, stopLightingTime, stopSAOTime, stopPostprocessTime, stopForwardTime, stopGUITime;

    unsigned int queryIDGeometry[2];
    unsigned int queryIDLighting[2];
    unsigned int queryIDSAO[2];
    unsigned int queryIDPostprocess[2];
    unsigned int queryIDForward[2];
    unsigned int queryIDGUI[2];

    glGenQueries(2, queryIDGeometry);
    glGenQueries(2, queryIDLighting);
    glGenQueries(2, queryIDSAO);
    glGenQueries(2, queryIDPostprocess);
    glGenQueries(2, queryIDForward);
    glGenQueries(2, queryIDGUI);


    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);


    while (!glfwWindowShouldClose(window))
    {
        GLfloat currentFrame = glfwGetTime();
        deltaTime = currentFrame - lastFrame;
        lastFrame = currentFrame;

        glfwPollEvents();
        cameraMove();


        //--------------
        // ImGui setting
        //--------------
        imGuiSetup();


        //------------------------
        // Geometry Pass rendering
        //------------------------
        glQueryCounter(queryIDGeometry[0], GL_TIMESTAMP);
        glBindFramebuffer(GL_FRAMEBUFFER, gBuffer);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Camera setting
        glm::mat4 projection = glm::perspective(camera.cameraFOV, (float)WIDTH / (float)HEIGHT, 0.1f, 100.0f);
        glm::mat4 view = camera.GetViewMatrix();
        glm::mat4 model;

        // Model(s) rendering
        gBufferShader.useShader();

        glUniformMatrix4fv(glGetUniformLocation(gBufferShader.Program, "projection"), 1, GL_FALSE, glm::value_ptr(projection));
        glUniformMatrix4fv(glGetUniformLocation(gBufferShader.Program, "view"), 1, GL_FALSE, glm::value_ptr(view));

        GLfloat rotationAngle = glfwGetTime() / 5.0f * modelRotationSpeed;
        model = glm::mat4();
        model = glm::translate(model, modelPosition);
        model = glm::rotate(model, rotationAngle, modelRotationAxis);
        model = glm::scale(model, modelScale);

        projViewModel = projection * view * model;

        glUniformMatrix4fv(glGetUniformLocation(gBufferShader.Program, "projViewModel"), 1, GL_FALSE, glm::value_ptr(projViewModel));
        glUniformMatrix4fv(glGetUniformLocation(gBufferShader.Program, "prevProjViewModel"), 1, GL_FALSE, glm::value_ptr(prevProjViewModel));
        glUniformMatrix4fv(glGetUniformLocation(gBufferShader.Program, "model"), 1, GL_FALSE, glm::value_ptr(model));
        glUniform3f(glGetUniformLocation(gBufferShader.Program, "albedoColor"), albedoColor.r, albedoColor.g, albedoColor.b);

        // Material
        // pbrMat.renderToShader();

        glActiveTexture(GL_TEXTURE0);
        objectAlbedo.useTexture();
        glUniform1i(glGetUniformLocation(gBufferShader.Program, "texAlbedo"), 0);
        glActiveTexture(GL_TEXTURE1);
        objectNormal.useTexture();
        glUniform1i(glGetUniformLocation(gBufferShader.Program, "texNormal"), 1);
        glActiveTexture(GL_TEXTURE2);
        objectRoughness.useTexture();
        glUniform1i(glGetUniformLocation(gBufferShader.Program, "texRoughness"), 2);
        glActiveTexture(GL_TEXTURE3);
        objectMetalness.useTexture();
        glUniform1i(glGetUniformLocation(gBufferShader.Program, "texMetalness"), 3);
        glActiveTexture(GL_TEXTURE4);
        objectAO.useTexture();
        glUniform1i(glGetUniformLocation(gBufferShader.Program, "texAO"), 4);

        objectModel.Draw();

        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glQueryCounter(queryIDGeometry[1], GL_TIMESTAMP);

        prevProjViewModel = projViewModel;

        //---------------
        // sao rendering
        //---------------
        glQueryCounter(queryIDSAO[0], GL_TIMESTAMP);
        glBindFramebuffer(GL_FRAMEBUFFER, saoFBO);
        glClear(GL_COLOR_BUFFER_BIT);

        if (saoMode)
        {
            // SAO noisy texture
            saoShader.useShader();

            glActiveTexture(GL_TEXTURE0);
            glBindTexture(GL_TEXTURE_2D, gPosition);
            glActiveTexture(GL_TEXTURE1);
            glBindTexture(GL_TEXTURE_2D, gNormal);

            glUniform1i(glGetUniformLocation(saoShader.Program, "saoSamples"), saoSamples);
            glUniform1f(glGetUniformLocation(saoShader.Program, "saoRadius"), saoRadius);
            glUniform1i(glGetUniformLocation(saoShader.Program, "saoTurns"), saoTurns);
            glUniform1f(glGetUniformLocation(saoShader.Program, "saoBias"), saoBias);
            glUniform1f(glGetUniformLocation(saoShader.Program, "saoScale"), saoScale);
            glUniform1f(glGetUniformLocation(saoShader.Program, "saoContrast"), saoContrast);
            glUniform1i(glGetUniformLocation(saoShader.Program, "viewportWidth"), WIDTH);
            glUniform1i(glGetUniformLocation(saoShader.Program, "viewportHeight"), HEIGHT);

            quadRender.drawShape();

            glBindFramebuffer(GL_FRAMEBUFFER, 0);

            // SAO blur pass
            glBindFramebuffer(GL_FRAMEBUFFER, saoBlurFBO);
            glClear(GL_COLOR_BUFFER_BIT);

            saoBlurShader.useShader();

            glUniform1i(glGetUniformLocation(saoBlurShader.Program, "saoBlurSize"), saoBlurSize);
            glActiveTexture(GL_TEXTURE0);
            glBindTexture(GL_TEXTURE_2D, saoBuffer);

            quadRender.drawShape();
        }

        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glQueryCounter(queryIDSAO[1], GL_TIMESTAMP);


        //------------------------
        // Lighting Pass rendering
        //------------------------
        glQueryCounter(queryIDLighting[0], GL_TIMESTAMP);
        glBindFramebuffer(GL_FRAMEBUFFER, postprocessFBO);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        lightingBRDFShader.useShader();

        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, gPosition);
        glActiveTexture(GL_TEXTURE1);
        glBindTexture(GL_TEXTURE_2D, gAlbedo);
        glActiveTexture(GL_TEXTURE2);
        glBindTexture(GL_TEXTURE_2D, gNormal);
        glActiveTexture(GL_TEXTURE3);
        glBindTexture(GL_TEXTURE_2D, gEffects);
        glActiveTexture(GL_TEXTURE4);
        glBindTexture(GL_TEXTURE_2D, saoBlurBuffer);
        glActiveTexture(GL_TEXTURE5);
        envMapHDR.useTexture();
        glActiveTexture(GL_TEXTURE6);
        envMapIrradiance.useTexture();
        glActiveTexture(GL_TEXTURE7);
        envMapPrefilter.useTexture();
        glActiveTexture(GL_TEXTURE8);
        envMapLUT.useTexture();

        lightPoint1.setLightPosition(lightPointPosition1);
        lightPoint2.setLightPosition(lightPointPosition2);
        lightPoint3.setLightPosition(lightPointPosition3);
        lightPoint1.setLightColor(glm::vec4(lightPointColor1, 1.0f));
        lightPoint2.setLightColor(glm::vec4(lightPointColor2, 1.0f));
        lightPoint3.setLightColor(glm::vec4(lightPointColor3, 1.0f));
        lightPoint1.setLightRadius(lightPointRadius1);
        lightPoint2.setLightRadius(lightPointRadius2);
        lightPoint3.setLightRadius(lightPointRadius3);

        for (int i = 0; i < Light::lightPointList.size(); i++)
        {
            Light::lightPointList[i].renderToShader(lightingBRDFShader, camera);
        }

        lightDirectional1.setLightDirection(lightDirectionalDirection1);
        lightDirectional1.setLightColor(glm::vec4(lightDirectionalColor1, 1.0f));

        for (int i = 0; i < Light::lightDirectionalList.size(); i++)
        {
            Light::lightDirectionalList[i].renderToShader(lightingBRDFShader, camera);
        }

        glUniformMatrix4fv(glGetUniformLocation(lightingBRDFShader.Program, "inverseView"), 1, GL_FALSE, glm::value_ptr(glm::transpose(view)));
        glUniformMatrix4fv(glGetUniformLocation(lightingBRDFShader.Program, "inverseProj"), 1, GL_FALSE, glm::value_ptr(glm::inverse(projection)));
        glUniformMatrix4fv(glGetUniformLocation(lightingBRDFShader.Program, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniform1f(glGetUniformLocation(lightingBRDFShader.Program, "materialRoughness"), materialRoughness);
        glUniform1f(glGetUniformLocation(lightingBRDFShader.Program, "materialMetallicity"), materialMetallicity);
        glUniform3f(glGetUniformLocation(lightingBRDFShader.Program, "materialF0"), materialF0.r, materialF0.g, materialF0.b);
        glUniform1f(glGetUniformLocation(lightingBRDFShader.Program, "ambientIntensity"), ambientIntensity);
        glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "gBufferView"), gBufferView);
        glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "pointMode"), pointMode);
        glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "directionalMode"), directionalMode);
        glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "iblMode"), iblMode);
        glUniform1i(glGetUniformLocation(lightingBRDFShader.Program, "attenuationMode"), attenuationMode);

        quadRender.drawShape();

        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glQueryCounter(queryIDLighting[1], GL_TIMESTAMP);


        //-------------------------------
        // Post-processing Pass rendering
        //-------------------------------
        glQueryCounter(queryIDPostprocess[0], GL_TIMESTAMP);
        glClear(GL_COLOR_BUFFER_BIT);

        firstpassPPShader.useShader();
        glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "gBufferView"), gBufferView);
        glUniform2f(glGetUniformLocation(firstpassPPShader.Program, "screenTextureSize"), 1.0f / WIDTH, 1.0f / HEIGHT);
        glUniform1f(glGetUniformLocation(firstpassPPShader.Program, "cameraAperture"), cameraAperture);
        glUniform1f(glGetUniformLocation(firstpassPPShader.Program, "cameraShutterSpeed"), cameraShutterSpeed);
        glUniform1f(glGetUniformLocation(firstpassPPShader.Program, "cameraISO"), cameraISO);
        glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "saoMode"), saoMode);
        glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "fxaaMode"), fxaaMode);
        glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "motionBlurMode"), motionBlurMode);
        glUniform1f(glGetUniformLocation(firstpassPPShader.Program, "motionBlurScale"), int(ImGui::GetIO().Framerate) / 60.0f);
        glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "motionBlurMaxSamples"), motionBlurMaxSamples);
        glUniform1i(glGetUniformLocation(firstpassPPShader.Program, "tonemappingMode"), tonemappingMode);

        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, postprocessBuffer);
        glActiveTexture(GL_TEXTURE1);
        glBindTexture(GL_TEXTURE_2D, saoBlurBuffer);
        glActiveTexture(GL_TEXTURE2);
        glBindTexture(GL_TEXTURE_2D, gEffects);

        quadRender.drawShape();

        glQueryCounter(queryIDPostprocess[1], GL_TIMESTAMP);


        //-----------------------
        // Forward Pass rendering
        //-----------------------
        glQueryCounter(queryIDForward[0], GL_TIMESTAMP);
        glBindFramebuffer(GL_READ_FRAMEBUFFER, gBuffer);
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0);

        // Copy the depth informations from the Geometry Pass into the default framebuffer
        glBlitFramebuffer(0, 0, WIDTH, HEIGHT, 0, 0, WIDTH, HEIGHT, GL_DEPTH_BUFFER_BIT, GL_NEAREST);
        glBindFramebuffer(GL_FRAMEBUFFER, 0);

        // Shape(s) rendering
        if (pointMode)
        {
            simpleShader.useShader();
            glUniformMatrix4fv(glGetUniformLocation(simpleShader.Program, "projection"), 1, GL_FALSE, glm::value_ptr(projection));
            glUniformMatrix4fv(glGetUniformLocation(simpleShader.Program, "view"), 1, GL_FALSE, glm::value_ptr(view));

            for (int i = 0; i < Light::lightPointList.size(); i++)
            {
                glUniform4f(glGetUniformLocation(simpleShader.Program, "lightColor"), Light::lightPointList[i].getLightColor().r, Light::lightPointList[i].getLightColor().g, Light::lightPointList[i].getLightColor().b, Light::lightPointList[i].getLightColor().a);

                if (Light::lightPointList[i].isMesh())
                    Light::lightPointList[i].lightMesh.drawShape(simpleShader, view, projection, camera);
            }
        }
        glQueryCounter(queryIDForward[1], GL_TIMESTAMP);


        //----------------
        // ImGui rendering
        //----------------
        glQueryCounter(queryIDGUI[0], GL_TIMESTAMP);
        ImGui::Render();
        glQueryCounter(queryIDGUI[1], GL_TIMESTAMP);


        //--------------
        // GPU profiling
        //--------------
        GLint stopGeometryTimerAvailable = 0;
        GLint stopLightingTimerAvailable = 0;
        GLint stopSAOTimerAvailable = 0;
        GLint stopPostprocessTimerAvailable = 0;
        GLint stopForwardTimerAvailable = 0;
        GLint stopGUITimerAvailable = 0;

        while (!stopGeometryTimerAvailable && !stopLightingTimerAvailable && !stopSAOTimerAvailable && !stopPostprocessTimerAvailable && !stopForwardTimerAvailable && !stopGUITimerAvailable)
        {
            glGetQueryObjectiv(queryIDGeometry[1], GL_QUERY_RESULT_AVAILABLE, &stopGeometryTimerAvailable);
            glGetQueryObjectiv(queryIDLighting[1], GL_QUERY_RESULT_AVAILABLE, &stopLightingTimerAvailable);
            glGetQueryObjectiv(queryIDSAO[1], GL_QUERY_RESULT_AVAILABLE, &stopSAOTimerAvailable);
            glGetQueryObjectiv(queryIDPostprocess[1], GL_QUERY_RESULT_AVAILABLE, &stopPostprocessTimerAvailable);
            glGetQueryObjectiv(queryIDForward[1], GL_QUERY_RESULT_AVAILABLE, &stopForwardTimerAvailable);
            glGetQueryObjectiv(queryIDGUI[1], GL_QUERY_RESULT_AVAILABLE, &stopGUITimerAvailable);
        }

        glGetQueryObjectui64v(queryIDGeometry[0], GL_QUERY_RESULT, &startGeometryTime);
        glGetQueryObjectui64v(queryIDGeometry[1], GL_QUERY_RESULT, &stopGeometryTime);
        glGetQueryObjectui64v(queryIDLighting[0], GL_QUERY_RESULT, &startLightingTime);
        glGetQueryObjectui64v(queryIDLighting[1], GL_QUERY_RESULT, &stopLightingTime);
        glGetQueryObjectui64v(queryIDSAO[0], GL_QUERY_RESULT, &startSAOTime);
        glGetQueryObjectui64v(queryIDSAO[1], GL_QUERY_RESULT, &stopSAOTime);
        glGetQueryObjectui64v(queryIDPostprocess[0], GL_QUERY_RESULT, &startPostprocessTime);
        glGetQueryObjectui64v(queryIDPostprocess[1], GL_QUERY_RESULT, &stopPostprocessTime);
        glGetQueryObjectui64v(queryIDForward[0], GL_QUERY_RESULT, &startForwardTime);
        glGetQueryObjectui64v(queryIDForward[1], GL_QUERY_RESULT, &stopForwardTime);
        glGetQueryObjectui64v(queryIDGUI[0], GL_QUERY_RESULT, &startGUITime);
        glGetQueryObjectui64v(queryIDGUI[1], GL_QUERY_RESULT, &stopGUITime);

        deltaGeometryTime = (stopGeometryTime - startGeometryTime) / 1000000.0;
        deltaLightingTime = (stopLightingTime - startLightingTime) / 1000000.0;
        deltaSAOTime = (stopSAOTime - startSAOTime) / 1000000.0;
        deltaPostprocessTime = (stopPostprocessTime - startPostprocessTime) / 1000000.0;
        deltaForwardTime = (stopForwardTime - startForwardTime) / 1000000.0;
        deltaGUITime = (stopGUITime - startGUITime) / 1000000.0;

        glfwSwapBuffers(window);
    }

    //---------
    // Cleaning
    //---------
    ImGui_ImplGlfwGL3_Shutdown();
    glfwTerminate();

    return 0;
}



void cameraMove()
{
    if (keys[GLFW_KEY_W])
        camera.keyboardCall(FORWARD, deltaTime);
    if (keys[GLFW_KEY_S])
        camera.keyboardCall(BACKWARD, deltaTime);
    if (keys[GLFW_KEY_A])
        camera.keyboardCall(LEFT, deltaTime);
    if (keys[GLFW_KEY_D])
        camera.keyboardCall(RIGHT, deltaTime);
}


void imGuiSetup()
{
    ImGui_ImplGlfwGL3_NewFrame();

    ImGui::Begin("Parallel-Deferred-Renderer", &guiIsOpen, ImVec2(0, 0), 0.5f, ImGuiWindowFlags_AlwaysUseWindowPadding | ImGuiWindowFlags_NoSavedSettings);
    ImGui::SetWindowSize(ImVec2(350, HEIGHT));

    if (ImGui::CollapsingHeader("Rendering", 0, true, true))
    {
        if (ImGui::TreeNode("Material"))
        {
            ImGui::ColorEdit3("Albedo", (float*)&albedoColor);
            ImGui::SliderFloat("Roughness", &materialRoughness, 0.0f, 1.0f);
            ImGui::SliderFloat("Metalness", &materialMetallicity, 0.0f, 1.0f);
            ImGui::SliderFloat3("F0", (float*)&materialF0, 0.0f, 1.0f);
            ImGui::SliderFloat("Ambient Intensity", &ambientIntensity, 0.0f, 1.0f);

            ImGui::TreePop();
        }

        if (ImGui::TreeNode("Lighting"))
        {
            if (ImGui::TreeNode("Mode"))
            {
                ImGui::Checkbox("Point", &pointMode);
                ImGui::Checkbox("Directional", &directionalMode);
                ImGui::Checkbox("Image-Based Lighting", &iblMode);

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("Point"))
            {
                if (ImGui::TreeNode("Position"))
                {
                    ImGui::SliderFloat3("Point 1", (float*)&lightPointPosition1, -5.0f, 5.0f);
                    ImGui::SliderFloat3("Point 2", (float*)&lightPointPosition2, -5.0f, 5.0f);
                    ImGui::SliderFloat3("Point 3", (float*)&lightPointPosition3, -5.0f, 5.0f);

                    ImGui::TreePop();
                }

                if (ImGui::TreeNode("Color"))
                {
                    ImGui::ColorEdit3("Point 1", (float*)&lightPointColor1);
                    ImGui::ColorEdit3("Point 2", (float*)&lightPointColor2);
                    ImGui::ColorEdit3("Point 3", (float*)&lightPointColor3);

                    ImGui::TreePop();
                }

                if (ImGui::TreeNode("Radius"))
                {
                    ImGui::SliderFloat("Point 1", &lightPointRadius1, 0.0f, 10.0f);
                    ImGui::SliderFloat("Point 2", &lightPointRadius2, 0.0f, 10.0f);
                    ImGui::SliderFloat("Point 3", &lightPointRadius3, 0.0f, 10.0f);

                    ImGui::TreePop();
                }

                if (ImGui::TreeNode("Attenuation"))
                {
                    ImGui::RadioButton("Quadratic", &attenuationMode, 1);
                    ImGui::RadioButton("UE4", &attenuationMode, 2);

                    ImGui::TreePop();
                }

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("Directional"))
            {
                if (ImGui::TreeNode("Direction"))
                {
                    ImGui::SliderFloat3("Direction 1", (float*)&lightDirectionalDirection1, -5.0f, 5.0f);

                    ImGui::TreePop();
                }

                if (ImGui::TreeNode("Color"))
                {
                    ImGui::ColorEdit3("Direct. 1", (float*)&lightDirectionalColor1);

                    ImGui::TreePop();
                }

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("Environment map"))
            {
                if (ImGui::Button("Appartment"))
                {
                    envMapHDR.setTextureHDR("resources/textures/hdr/appart.hdr", "appartHDR", true);
                    iblSetup();
                }

                if (ImGui::Button("Pisa"))
                {
                    envMapHDR.setTextureHDR("resources/textures/hdr/pisa.hdr", "pisaHDR", true);
                    iblSetup();
                }

                if (ImGui::Button("Canyon"))
                {
                    envMapHDR.setTextureHDR("resources/textures/hdr/canyon.hdr", "canyonHDR", true);
                    iblSetup();
                }

                if (ImGui::Button("Loft"))
                {
                    envMapHDR.setTextureHDR("resources/textures/hdr/loft.hdr", "loftHDR", true);
                    iblSetup();
                }

                if (ImGui::Button("Path"))
                {
                    envMapHDR.setTextureHDR("resources/textures/hdr/path.hdr", "pathHDR", true);
                    iblSetup();
                }

                if (ImGui::Button("Circus"))
                {
                    envMapHDR.setTextureHDR("resources/textures/hdr/circus.hdr", "circusHDR", true);
                    iblSetup();
                }

                ImGui::TreePop();
            }

            ImGui::TreePop();
        }

        if (ImGui::TreeNode("Post processing"))
        {
            if (ImGui::TreeNode("SAO"))
            {
                ImGui::Checkbox("Enable", &saoMode);

                ImGui::SliderInt("Samples", &saoSamples, 0, 64);
                ImGui::SliderFloat("Radius", &saoRadius, 0.0f, 3.0f);
                ImGui::SliderInt("Turns", &saoTurns, 0, 16);
                ImGui::SliderFloat("Bias", &saoBias, 0.0f, 0.1f);
                ImGui::SliderFloat("Scale", &saoScale, 0.0f, 3.0f);
                ImGui::SliderFloat("Contrast", &saoContrast, 0.0f, 3.0f);
                ImGui::SliderInt("Blur Size", &saoBlurSize, 0, 8);

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("FXAA"))
            {
                ImGui::Checkbox("Enable", &fxaaMode);

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("Motion Blur"))
            {
                ImGui::Checkbox("Enable", &motionBlurMode);
                ImGui::SliderInt("Max Samples", &motionBlurMaxSamples, 1, 128);

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("Tonemapping"))
            {
                ImGui::RadioButton("Reinhard", &tonemappingMode, 1);
                ImGui::RadioButton("Filmic", &tonemappingMode, 2);
                ImGui::RadioButton("Uncharted", &tonemappingMode, 3);

                ImGui::TreePop();
            }

            ImGui::TreePop();
        }

        if (ImGui::TreeNode("Camera"))
        {
            ImGui::SliderFloat("Aperture", &cameraAperture, 1.0f, 32.0f);
            ImGui::SliderFloat("Shutter Speed", &cameraShutterSpeed, 0.001f, 1.0f);
            ImGui::SliderFloat("ISO", &cameraISO, 100.0f, 3200.0f);

            ImGui::TreePop();
        }

        if (ImGui::TreeNode("Object"))
        {
            ImGui::SliderFloat3("Position", (float*)&modelPosition, -5.0f, 5.0f);
            ImGui::SliderFloat("Rotation Speed", &modelRotationSpeed, 0.0f, 50.0f);
            ImGui::SliderFloat3("Rotation Axis", (float*)&modelRotationAxis, 0.0f, 1.0f);

            if (ImGui::TreeNode("Model"))
            {
                if (ImGui::Button("Sphere"))
                {
                    objectModel.~Model();
                    objectModel.loadModel("resources/models/sphere/sphere.obj");
                    modelScale = glm::vec3(0.6f);
                }

                if (ImGui::Button("Teapot"))
                {
                    objectModel.~Model();
                    objectModel.loadModel("resources/models/teapot/teapot.obj");
                    modelScale = glm::vec3(0.6f);
                }

                if (ImGui::Button("Shader ball"))
                {
                    objectModel.~Model();
                    objectModel.loadModel("resources/models/shaderball/shaderball.obj");
                    modelScale = glm::vec3(0.1f);
                }

                ImGui::TreePop();
            }

            if (ImGui::TreeNode("Material"))
            {
                if (ImGui::Button("Rusted iron"))
                {
                    objectAlbedo.setTexture("resources/textures/pbr/rustediron/rustediron_albedo.png", "ironAlbedo", true);
                    objectNormal.setTexture("resources/textures/pbr/rustediron/rustediron_normal.png", "ironNormal", true);
                    objectRoughness.setTexture("resources/textures/pbr/rustediron/rustediron_roughness.png", "ironRoughness", true);
                    objectMetalness.setTexture("resources/textures/pbr/rustediron/rustediron_metalness.png", "ironMetalness", true);
                    objectAO.setTexture("resources/textures/pbr/rustediron/rustediron_ao.png", "ironAO", true);

                    materialF0 = glm::vec3(0.04f);
                }

                if (ImGui::Button("Gold"))
                {
                    objectAlbedo.setTexture("resources/textures/pbr/gold/gold_albedo.png", "goldAlbedo", true);
                    objectNormal.setTexture("resources/textures/pbr/gold/gold_normal.png", "goldNormal", true);
                    objectRoughness.setTexture("resources/textures/pbr/gold/gold_roughness.png", "goldRoughness", true);
                    objectMetalness.setTexture("resources/textures/pbr/gold/gold_metalness.png", "goldMetalness", true);
                    objectAO.setTexture("resources/textures/pbr/gold/gold_ao.png", "goldAO", true);

                    materialF0 = glm::vec3(1.0f, 0.72f, 0.29f);
                }

                if (ImGui::Button("Woodfloor"))
                {
                    objectAlbedo.setTexture("resources/textures/pbr/woodfloor/woodfloor_albedo.png", "woodfloorAlbedo", true);
                    objectNormal.setTexture("resources/textures/pbr/woodfloor/woodfloor_normal.png", "woodfloorNormal", true);
                    objectRoughness.setTexture("resources/textures/pbr/woodfloor/woodfloor_roughness.png", "woodfloorRoughness", true);
                    objectMetalness.setTexture("resources/textures/pbr/woodfloor/woodfloor_metalness.png", "woodfloorMetalness", true);
                    objectAO.setTexture("resources/textures/pbr/woodfloor/woodfloor_ao.png", "woodfloorAO", true);

                    materialF0 = glm::vec3(0.04f);
                }

                ImGui::TreePop();
            }

            ImGui::TreePop();
        }
    }

    if (ImGui::CollapsingHeader("Profiling", 0, true, true))
    {
        ImGui::Text("Geometry Pass :    %.4f ms", deltaGeometryTime);
        ImGui::Text("Lighting Pass :    %.4f ms", deltaLightingTime);
        ImGui::Text("SAO Pass :         %.4f ms", deltaSAOTime);
        ImGui::Text("Postprocess Pass : %.4f ms", deltaPostprocessTime);
        ImGui::Text("Forward Pass :     %.4f ms", deltaForwardTime);
        ImGui::Text("GUI Pass :         %.4f ms", deltaGUITime);
    }

    if (ImGui::CollapsingHeader("Application Info", 0, true, true))
    {
        char* glInfos = (char*)glGetString(GL_VERSION);
        char* hardwareInfos = (char*)glGetString(GL_RENDERER);

        ImGui::Text("OpenGL Version :");
        ImGui::Text(glInfos);
        ImGui::Text("Hardware Informations :");
        ImGui::Text(hardwareInfos);
        ImGui::Text("\nFramerate %.2f FPS / Frametime %.4f ms", ImGui::GetIO().Framerate, 1000.0f / ImGui::GetIO().Framerate);
    }

    if (ImGui::CollapsingHeader("About", 0, true, true))
    {
        ImGui::Text("Parallel-Deferred-Renderer");
    }

    ImGui::End();
}


void gBufferSetup()
{
    glGenFramebuffers(1, &gBuffer);
    glBindFramebuffer(GL_FRAMEBUFFER, gBuffer);

    // Position
    glGenTextures(1, &gPosition);
    glBindTexture(GL_TEXTURE_2D, gPosition);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, WIDTH, HEIGHT, 0, GL_RGBA, GL_FLOAT, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, gPosition, 0);

    // Albedo + Roughness
    glGenTextures(1, &gAlbedo);
    glBindTexture(GL_TEXTURE_2D, gAlbedo);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1, GL_TEXTURE_2D, gAlbedo, 0);

    // Normals + Metalness
    glGenTextures(1, &gNormal);
    glBindTexture(GL_TEXTURE_2D, gNormal);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, WIDTH, HEIGHT, 0, GL_RGBA, GL_FLOAT, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT2, GL_TEXTURE_2D, gNormal, 0);

    // Effects (AO + Velocity)
    glGenTextures(1, &gEffects);
    glBindTexture(GL_TEXTURE_2D, gEffects);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, WIDTH, HEIGHT, 0, GL_RGB, GL_FLOAT, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT3, GL_TEXTURE_2D, gEffects, 0);

    // Define the COLOR_ATTACHMENTS for the G-Buffer
    GLuint attachments[4] = { GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT1, GL_COLOR_ATTACHMENT2, GL_COLOR_ATTACHMENT3 };
    glDrawBuffers(4, attachments);

    // Z-Buffer
    glGenRenderbuffers(1, &zBuffer);
    glBindRenderbuffer(GL_RENDERBUFFER, zBuffer);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, WIDTH, HEIGHT);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, zBuffer);

    // Check if the framebuffer is complete before continuing
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        std::cout << "Framebuffer not complete !" << std::endl;
}


void saoSetup()
{
    // SAO Buffer
    glGenFramebuffers(1, &saoFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, saoFBO);
    glGenTextures(1, &saoBuffer);
    glBindTexture(GL_TEXTURE_2D, saoBuffer);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, WIDTH, HEIGHT, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, saoBuffer, 0);

    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        std::cout << "SAO Framebuffer not complete !" << std::endl;

    // SAO Blur Buffer
    glGenFramebuffers(1, &saoBlurFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, saoBlurFBO);
    glGenTextures(1, &saoBlurBuffer);
    glBindTexture(GL_TEXTURE_2D, saoBlurBuffer);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, WIDTH, HEIGHT, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, saoBlurBuffer, 0);

    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        std::cout << "SAO Blur Framebuffer not complete !" << std::endl;

    glBindFramebuffer(GL_FRAMEBUFFER, 0);
}


void postprocessSetup()
{
    // Post-processing Buffer
    glGenFramebuffers(1, &postprocessFBO);
    glBindFramebuffer(GL_FRAMEBUFFER, postprocessFBO);

    glGenTextures(1, &postprocessBuffer);
    glBindTexture(GL_TEXTURE_2D, postprocessBuffer);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, WIDTH, HEIGHT, 0, GL_RGBA, GL_FLOAT, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, postprocessBuffer, 0);

    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        std::cout << "Postprocess Framebuffer not complete !" << std::endl;
}


void iblSetup()
{
    // Latlong to Cubemap conversion
    glGenFramebuffers(1, &envToCubeFBO);
    glGenRenderbuffers(1, &envToCubeRBO);
    glBindFramebuffer(GL_FRAMEBUFFER, envToCubeFBO);
    glBindRenderbuffer(GL_RENDERBUFFER, envToCubeRBO);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, envMapCube.getTexWidth(), envMapCube.getTexHeight());
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, envToCubeRBO);

    latlongToCubeShader.useShader();

    glUniformMatrix4fv(glGetUniformLocation(latlongToCubeShader.Program, "projection"), 1, GL_FALSE, glm::value_ptr(envMapProjection));
    glActiveTexture(GL_TEXTURE0);
    envMapHDR.useTexture();

    glViewport(0, 0, envMapCube.getTexWidth(), envMapCube.getTexHeight());
    glBindFramebuffer(GL_FRAMEBUFFER, envToCubeFBO);

    for (unsigned int i = 0; i < 6; ++i)
    {
        glUniformMatrix4fv(glGetUniformLocation(latlongToCubeShader.Program, "view"), 1, GL_FALSE, glm::value_ptr(envMapView[i]));
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, envMapCube.getTexID(), 0);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        envCubeRender.drawShape();
    }

    envMapCube.computeTexMipmap();

    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    // Diffuse irradiance capture
    glGenFramebuffers(1, &irradianceFBO);
    glGenRenderbuffers(1, &irradianceRBO);
    glBindFramebuffer(GL_FRAMEBUFFER, irradianceFBO);
    glBindRenderbuffer(GL_RENDERBUFFER, irradianceRBO);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, envMapIrradiance.getTexWidth(), envMapIrradiance.getTexHeight());

    irradianceIBLShader.useShader();

    glUniformMatrix4fv(glGetUniformLocation(irradianceIBLShader.Program, "projection"), 1, GL_FALSE, glm::value_ptr(envMapProjection));
    glActiveTexture(GL_TEXTURE0);
    envMapCube.useTexture();

    glViewport(0, 0, envMapIrradiance.getTexWidth(), envMapIrradiance.getTexHeight());
    glBindFramebuffer(GL_FRAMEBUFFER, irradianceFBO);

    for (unsigned int i = 0; i < 6; ++i)
    {
        glUniformMatrix4fv(glGetUniformLocation(irradianceIBLShader.Program, "view"), 1, GL_FALSE, glm::value_ptr(envMapView[i]));
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, envMapIrradiance.getTexID(), 0);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        envCubeRender.drawShape();
    }

    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    // Prefilter cubemap
    prefilterIBLShader.useShader();

    glUniformMatrix4fv(glGetUniformLocation(prefilterIBLShader.Program, "projection"), 1, GL_FALSE, glm::value_ptr(envMapProjection));
    envMapCube.useTexture();

    glGenFramebuffers(1, &prefilterFBO);
    glGenRenderbuffers(1, &prefilterRBO);
    glBindFramebuffer(GL_FRAMEBUFFER, prefilterFBO);

    unsigned int maxMipLevels = 5;

    for (unsigned int mip = 0; mip < maxMipLevels; ++mip)
    {
        unsigned int mipWidth = envMapPrefilter.getTexWidth() * std::pow(0.5, mip);
        unsigned int mipHeight = envMapPrefilter.getTexHeight() * std::pow(0.5, mip);

        glBindRenderbuffer(GL_RENDERBUFFER, prefilterRBO);
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, mipWidth, mipHeight);

        glViewport(0, 0, mipWidth, mipHeight);

        float roughness = (float)mip / (float)(maxMipLevels - 1);

        glUniform1f(glGetUniformLocation(prefilterIBLShader.Program, "roughness"), roughness);
        glUniform1f(glGetUniformLocation(prefilterIBLShader.Program, "cubeResolutionWidth"), envMapPrefilter.getTexWidth());
        glUniform1f(glGetUniformLocation(prefilterIBLShader.Program, "cubeResolutionHeight"), envMapPrefilter.getTexHeight());

        for (unsigned int i = 0; i < 6; ++i)
        {
            glUniformMatrix4fv(glGetUniformLocation(prefilterIBLShader.Program, "view"), 1, GL_FALSE, glm::value_ptr(envMapView[i]));
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, envMapPrefilter.getTexID(), mip);

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

            envCubeRender.drawShape();
        }
    }

    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    // BRDF LUT
    glGenFramebuffers(1, &brdfLUTFBO);
    glGenRenderbuffers(1, &brdfLUTRBO);
    glBindFramebuffer(GL_FRAMEBUFFER, brdfLUTFBO);
    glBindRenderbuffer(GL_RENDERBUFFER, brdfLUTRBO);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, envMapLUT.getTexWidth(), envMapLUT.getTexHeight());
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, envMapLUT.getTexID(), 0);

    glViewport(0, 0, envMapLUT.getTexWidth(), envMapLUT.getTexHeight());
    integrateIBLShader.useShader();
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    quadRender.drawShape();

    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    glViewport(0, 0, WIDTH, HEIGHT);
}


static void error_callback(int error, const char* description)
{
    fprintf(stderr, "Error %d: %s\n", error, description);
}


void key_callback(GLFWwindow* window, int key, int scancode, int action, int mode)
{
    if (key == GLFW_KEY_ESCAPE && action == GLFW_PRESS)
        glfwSetWindowShouldClose(window, GL_TRUE);

    if (key == GLFW_KEY_F11 && action == GLFW_PRESS)
    {
        screenMode = !screenMode;


    }

    if (keys[GLFW_KEY_1])
        gBufferView = 1;

    if (keys[GLFW_KEY_2])
        gBufferView = 2;

    if (keys[GLFW_KEY_3])
        gBufferView = 3;

    if (keys[GLFW_KEY_4])
        gBufferView = 4;

    if (keys[GLFW_KEY_5])
        gBufferView = 5;

    if (keys[GLFW_KEY_6])
        gBufferView = 6;

    if (keys[GLFW_KEY_7])
        gBufferView = 7;

    if (keys[GLFW_KEY_8])
        gBufferView = 8;

    if (keys[GLFW_KEY_9])
        gBufferView = 9;

    if (key >= 0 && key < 1024)
    {
        if (action == GLFW_PRESS)
            keys[key] = true;
        else if (action == GLFW_RELEASE)
            keys[key] = false;
    }
}


void mouse_callback(GLFWwindow* window, double xpos, double ypos)
{
    if (firstMouse)
    {
        lastX = xpos;
        lastY = ypos;
        firstMouse = false;
    }

    GLfloat xoffset = xpos - lastX;
    GLfloat yoffset = lastY - ypos;
    lastX = xpos;
    lastY = ypos;

    if (cameraMode)
        camera.mouseCall(xoffset, yoffset);
}


void mouse_button_callback(GLFWwindow* window, int button, int action, int mods)
{
    if (button == GLFW_MOUSE_BUTTON_RIGHT && action == GLFW_PRESS)
        cameraMode = true;
    else
        cameraMode = false;
}


void scroll_callback(GLFWwindow* window, double xoffset, double yoffset)
{
    if (cameraMode)
        camera.scrollCall(yoffset);
}
