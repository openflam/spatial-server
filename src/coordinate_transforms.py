import numpy as np
from scipy.spatial.transform import Rotation

def homogenize(rotation, translation):
    """
    Combine the (3,3) rotation matrix and (3,) translation matrix to
    one (4,4) transformation matrix
    """
    homogenous_array = np.eye(4)
    homogenous_array[:3, :3] = rotation
    homogenous_array[:3, 3] = translation
    return homogenous_array

def convert_hloc_to_blender_frame(matrix):
    # Add 180 degrees to X - change in convention
    matrix = np.array(matrix)
    euler_xyz = Rotation.from_matrix(matrix[:3, :3]).as_euler("xyz", degrees = True)
    euler_xyz[0] += 180
    rotmat = Rotation.from_euler('xyz', euler_xyz, degrees = True).as_matrix()
    matrix[:3, :3] = rotmat
    return matrix

def convert_blender_to_aframe_frame(matrix):
    # Rotate -90 degrees along x-axis
    T_B_to_A = np.eye(4)
    T_B_to_A[:3,:3] = Rotation.from_euler('xyz', [-90,0,0], degrees = True).as_matrix()
    return T_B_to_A @ matrix

def rot_from_qvec(qvec):
    # Change (w,x,y,z) to (x,y,z,w)
    return Rotation.from_quat([qvec[1], qvec[2], qvec[3], qvec[0]])

def get_arscene_pose_matrix(aframe_camera_pose, ret_from_hloc):
    hloc_camera_matrix = np.linalg.inv(homogenize(
        rotation = rot_from_qvec(ret_from_hloc['qvec']).as_matrix(), 
        translation = ret_from_hloc['tvec'],
    ))
    blender_camera_matrix = convert_hloc_to_blender_frame(hloc_camera_matrix)
    blender_camera_matrix_in_aframe = convert_blender_to_aframe_frame(blender_camera_matrix)

    aframe_camera_matrix = np.array(aframe_camera_pose).reshape((4,4)).T

    arscene_pose_aframe = aframe_camera_matrix @ np.linalg.inv(blender_camera_matrix_in_aframe)

    return arscene_pose_aframe.T.flatten().tolist()