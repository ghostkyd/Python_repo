from datetime import datetime, date, timedelta

import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
        return result['encoding']

file_path = '/Users/stanleysun/Desktop/未命名文件夹/1865 Prelusion Launch Event Proposal-20240807.pdf'
encoding = detect_encoding(file_path)
print(f'The encoding of the file is: {encoding}')


# s = date.today()
# modified_date = s + timedelta(days=1)

# aa=datetime.today()
# print(aa)
# bb=aa + timedelta(days=1)
# print(bb)


# 
# import fbx
# from  FbxCommon import FbxNodeAttribute

# def get_mesh_faces(mesh):
#     polygon_count = mesh.GetPolygonCount()
#     polygon_vertices = []
#     for i in range(polygon_count):
#         polygon_size = mesh.GetPolygonSize(i)
#         for j in range(polygon_size):
#             vertex_index = mesh.GetPolygonVertex(i, j)
#             polygon_vertices.append(vertex_index)
#     return polygon_vertices

# # 创建FBX管理器
# manager = fbx.FbxManager.Create()

# # 创建场景
# scene = fbx.FbxScene.Create(manager, "MyScene")

# # 创建导入器
# importer = fbx.FbxImporter.Create(manager, "")

# # 加载FBX文件
# if importer.Initialize(r"D:\tool code\DataFile\E2UB_1013.fbx", -1, manager.GetIOSettings()):
#     importer.Import(scene)
#     importer.Destroy()

# # 输出场景信息
# print("场景名字:", scene.GetName())

# # 输出场景中对象的数量
# print("对象数量:", scene.GetNodeCount())

# # 访问场景中的节点
# root_node = scene.GetRootNode()
# print("根节点名字:", root_node.GetName())
# total_face_count = 0
# for i in range(root_node.GetChildCount()):
#     child_node = root_node.GetChild(i)
#     print("节点名字:", child_node.GetName())
#     mesh= child_node.GetMesh()
#     if mesh is not None:
#         face_count = mesh.GetPolygonCount()
#         total_face_count += face_count
# print("总面数:", total_face_count)

# # 释放FBX管理器
# manager.Destroy()
