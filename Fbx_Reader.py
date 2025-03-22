import fbx

def get_face_count(file_path):
    # Create an FBX manager
    manager = fbx.FbxManager.Create()

    # Create an IO settings object
    io_settings = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)

    # Set the IO settings to use the default values
    manager.SetIOSettings(io_settings)

    # Create an importer object
    importer = fbx.FbxImporter.Create(manager, '')

    # Use the importer to read the file
    importer.Initialize(file_path)

    # Create a scene object
    scene = fbx.FbxScene.Create(manager, 'myScene')

    # Use the importer to populate the scene with the file's contents
    importer.Import(scene)

    # Get the root node of the scene
    root_node = scene.GetRootNode()

    # Get the number of meshes in the scene
    mesh_count = root_node.GetChildCount(fbx.FbxCriteria.ObjectType(fbx.FbxMesh.ClassId))

    # Loop through each mesh and get the face count
    total_face_count = 0
    for i in range(mesh_count):
        mesh = root_node.GetChild(i)
        face_count = mesh.GetPolygonCount()
        total_face_count += face_count

    # Clean up the importer and manager
    importer.Destroy()
    manager.Destroy()

    return total_face_count

# Example usage
file_path = r'D:\tool code\DataFile\E2UB_1013.fbx'
face_count = get_face_count(file_path)
print('The file has', face_count, 'faces.')