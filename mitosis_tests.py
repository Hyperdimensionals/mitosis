import sys
sys.path.insert(0, 'Documents/Programming/Blender/mitosis')

import mitosis

import time

if __name__ == "__main__":
    time_start = time.time()

    # MeshCube Replication Tests #
    replicator_cube = mitosis.MeshCube_Replicator(
        offset=4, frames_to_spawn=5, scale_start=0, behavior="inflate")
    replicator_cube.generate(5)

    replicator_cylinder = mitosis.Cylinder_Replicator(
        start_x=-30, start_y=0, start_z=0,
        offset=4, frames_to_spawn=5, scale_start=0, behavior="DIVIDE")
    replicator_cylinder.generate(5)

    replicator_torus = mitosis.Torus_Replicator(
        offset=4, frames_to_spawn=5, scale_start=0, behavior="DIVIDE",
        start_x=30, start_y=0, start_z=0)
    replicator_torus.generate(5)

    print("Script duration: %.4f sec" % (time.time() - time_start))
