#pragma once
#include <omp.h>

#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <map>
#include <vector>

#include <glad/glad.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include "stb_image.h"
#include <assimp/Importer.hpp>
#include <assimp/scene.h>
#include <assimp/postprocess.h>

#include "model.h"
#include "mesh.h"


Model::Model()
{

}


Model::~Model()
{

}


void Model::loadModel(std::string path)
{
    Assimp::Importer importer;
    const aiScene* scene = importer.ReadFile(path, aiProcess_Triangulate | aiProcess_FlipUVs);

    if(!scene || scene->mFlags == AI_SCENE_FLAGS_INCOMPLETE || !scene->mRootNode) // if is Not Zero
    {
        std::cout << "ERROR::ASSIMP:: " << importer.GetErrorString() << std::endl;
        return;
    }

    this->directory = path.substr(0, path.find_last_of('/'));
    this->processNode(scene->mRootNode, scene);
}

void Model::Draw()
{
    for(GLuint i = 0; i < this->meshes.size(); i++)
        this->meshes[i].Draw();
}


void Model::processNode(aiNode* node, const aiScene* scene)
{
    for(GLuint i = 0; i < node->mNumMeshes; i++)
    {
        aiMesh* mesh = scene->mMeshes[node->mMeshes[i]];
        this->meshes.push_back(this->processMesh(mesh, scene));
    }

    for(GLuint i = 0; i < node->mNumChildren; i++)
    {
        this->processNode(node->mChildren[i], scene);
    }
}


// Parallelize vertex loading
Mesh Model::processMesh(aiMesh* mesh, const aiScene* scene)
{
    std::vector<Vertex> vertices(mesh->mNumVertices);
    std::vector<GLuint> indices;

    double startTotal = omp_get_wtime();
    double startVerts = omp_get_wtime();
    
#pragma omp parallel for
    for (int i = 0; i < (int)mesh->mNumVertices; i++)
    {
        Vertex vertex;
        glm::vec3 vector;

        vector.x = mesh->mVertices[i].x;
        vector.y = mesh->mVertices[i].y;
        vector.z = mesh->mVertices[i].z;
        vertex.Position = vector;

        vector.x = mesh->mNormals[i].x;
        vector.y = mesh->mNormals[i].y;
        vector.z = mesh->mNormals[i].z;
        vertex.Normal = vector;

        if (mesh->mTextureCoords[0])
        {
            glm::vec2 vec;
            vec.x = mesh->mTextureCoords[0][i].x;
            vec.y = mesh->mTextureCoords[0][i].y;
            vertex.TexCoords = vec;
        }
        else
        {
            vertex.TexCoords = glm::vec2(0.0f, 0.0f);
        }

        vertices[i] = vertex; 
    }

    double endVerts = omp_get_wtime();


    double startFaces = omp_get_wtime();

    size_t totalIndices = 0;
    for (unsigned int i = 0; i < mesh->mNumFaces; i++)
        totalIndices += mesh->mFaces[i].mNumIndices;

    indices.resize(totalIndices);

#pragma omp parallel for
    for (int i = 0; i < (int)mesh->mNumFaces; i++)
    {
        const aiFace& face = mesh->mFaces[i];
        for (unsigned int j = 0; j < face.mNumIndices; j++)
        {
            
            size_t globalIdx = i * 3 + j;
            indices[globalIdx] = face.mIndices[j];
        }
    }

    double endFaces = omp_get_wtime();
    double endTotal = omp_get_wtime();


    std::cout << "Vertex processing: " << (endVerts - startVerts) * 1000.0 << " ms" << std::endl;
    std::cout << "Face processing:   " << (endFaces - startFaces) * 1000.0 << " ms" << std::endl;
    std::cout << "Total time:        " << (endTotal - startTotal) * 1000.0 << " ms" << std::endl;

    return Mesh(vertices, indices);
}
