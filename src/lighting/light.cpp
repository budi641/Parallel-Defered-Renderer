#include <omp.h>
#include "light.h"
#include "shader.h"
#include "camera.h"

// basically, openGL can't be parallelized so we have to split the logic and the lib, ik this func sucks but wtv
void Light::renderAllToShader(Shader& shader, Camera& camera)
{
    std::cout << "Running with " << omp_get_max_threads() << " threads\n";
    shader.useShader();

    glm::mat4 viewMatrix = camera.GetViewMatrix();

    
    struct PointLightData {
        glm::vec3 positionViewSpace;
        glm::vec4 color;
        float radius;
        int id;
    };

    struct DirectionalLightData {
        glm::vec3 directionViewSpace;
        glm::vec4 color;
        int id;
    };

    std::vector<PointLightData> pointData(lightPointList.size());
    std::vector<DirectionalLightData> dirData(lightDirectionalList.size());

    // point light
#pragma omp parallel for schedule(static)
    for (int i = 0; i < (int)lightPointList.size(); ++i)
    {
        const Light& L = lightPointList[i];
        PointLightData d;
        d.positionViewSpace = glm::vec3(viewMatrix * glm::vec4(L.lightPosition, 1.0f));
        d.color = L.lightColor;
        d.radius = L.lightRadius;
        d.id = L.lightPointID;
        pointData[i] = d;
    }

    //dir light
#pragma omp parallel for schedule(static)
    for (int i = 0; i < (int)lightDirectionalList.size(); ++i)
    {
        const Light& L = lightDirectionalList[i];
        DirectionalLightData d;
        d.directionViewSpace = glm::vec3(viewMatrix * glm::vec4(L.lightDirection, 0.0f));
        d.color = L.lightColor;
        d.id = L.lightDirectionalID;
        dirData[i] = d;
    }

    //openGL part
    for (const auto& d : pointData)
    {
        std::string prefix = "lightPointArray[" + std::to_string(d.id) + "]";
        glUniform3f(glGetUniformLocation(shader.Program, (prefix + ".position").c_str()),
            d.positionViewSpace.x, d.positionViewSpace.y, d.positionViewSpace.z);
        glUniform4f(glGetUniformLocation(shader.Program, (prefix + ".color").c_str()),
            d.color.r, d.color.g, d.color.b, d.color.a);
        glUniform1f(glGetUniformLocation(shader.Program, (prefix + ".radius").c_str()),
            d.radius);
    }

    for (const auto& d : dirData)
    {
        std::string prefix = "lightDirectionalArray[" + std::to_string(d.id) + "]";
        glUniform3f(glGetUniformLocation(shader.Program, (prefix + ".direction").c_str()),
            d.directionViewSpace.x, d.directionViewSpace.y, d.directionViewSpace.z);
        glUniform4f(glGetUniformLocation(shader.Program, (prefix + ".color").c_str()),
            d.color.r, d.color.g, d.color.b, d.color.a);
    }
}

//too scared to delete those

GLuint Light::lightPointCount = 0;
GLuint Light::lightDirectionalCount = 0;
std::vector<Light> Light::lightPointList;
std::vector<Light> Light::lightDirectionalList;

Light::Light() {}
Light::~Light() {}

void Light::setLightPosition(glm::vec3 position)
{
    lightPosition = position;
}

void Light::setLightDirection(glm::vec3 direction)
{
    lightDirection = direction;
}

void Light::setLightColor(glm::vec4 color)
{
    lightColor = color;
}

void Light::setLightRadius(float radius)
{
    lightRadius = radius;
}

glm::vec3 Light::getLightPosition()
{
    return lightPosition;
}

glm::vec3 Light::getLightDirection()
{
    return lightDirection;
}

glm::vec4 Light::getLightColor()
{
    return lightColor;
}

float Light::getLightRadius()
{
    return lightRadius;
}

bool Light::isMesh()
{
    return lightToMesh;
}

void Light::renderToShader(Shader& shader, Camera& camera)
{
    
    shader.useShader();
    std::string prefix = "singleLight";
    glm::mat4 viewMatrix = camera.GetViewMatrix();
    glm::vec3 posView = glm::vec3(viewMatrix * glm::vec4(lightPosition, 1.0f));

    glUniform3f(glGetUniformLocation(shader.Program, (prefix + ".position").c_str()),
        posView.x, posView.y, posView.z);
    glUniform4f(glGetUniformLocation(shader.Program, (prefix + ".color").c_str()),
        lightColor.r, lightColor.g, lightColor.b, lightColor.a);
    glUniform1f(glGetUniformLocation(shader.Program, (prefix + ".radius").c_str()),
        lightRadius);
}

void Light::setLight(glm::vec3 position, glm::vec4 color, float radius, bool isMesh)
{
    lightType = "point";
    lightPosition = position;
    lightColor = color;
    lightRadius = radius;
    lightToMesh = isMesh;

    lightPointID = lightPointCount++;
    lightPointList.push_back(*this);
}

void Light::setLight(glm::vec3 direction, glm::vec4 color)
{
    lightType = "directional";
    lightDirection = direction;
    lightColor = color;

    lightDirectionalID = lightDirectionalCount++;
    lightDirectionalList.push_back(*this);
}
