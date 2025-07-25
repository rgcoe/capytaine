import pytest

import numpy as np
import capytaine as cpt

##################
#  Generate lid  #
##################

def test_lid_below_free_surface():
    mesh = cpt.AxialSymmetricMesh.from_profile(lambda z: (z + 1.0)**2, np.linspace(-1.0, 0.0, 10)).merged()
    lid_mesh = mesh.generate_lid(z=-0.5)
    x, y, z = lid_mesh.faces_centers.T
    assert np.all(np.hypot(x, y) <= (z + 1.0)**2)


def test_lid_below_body():
    mesh = cpt.mesh_sphere(radius=0.5, center=(0, 0, 0.0))
    lid_mesh = mesh.generate_lid(z=-2.0)
    assert lid_mesh.nb_vertices == 0


def test_lid_underwater_mesh():
    mesh = cpt.mesh_sphere(radius=0.5, center=(0, 0, -1.5))
    lid_mesh = mesh.generate_lid()
    assert lid_mesh.nb_vertices == 0


def test_lid_concave_body():
    pygmsh = pytest.importorskip("pygmsh")
    from capytaine.io.meshio import load_from_meshio
    d = 1.9
    with pygmsh.occ.Geometry() as geom:
        cyl1 = geom.add_cylinder([0, 0, 0], [0, 0, -1.0],  1.0)
        cyl2 = geom.add_cylinder([d, 0, 0], [0.0, 0, -1.0],  1.0)
        geom.boolean_union([cyl1, cyl2])
        gmsh_mesh = geom.generate_mesh(dim=2)
    mesh = load_from_meshio(gmsh_mesh)
    lid_mesh = mesh.generate_lid()
    def in_crown(x, y):
        return (np.hypot(x, y) < 1.0) | (np.hypot(x-d, y) < 1.0)
    assert all(in_crown(lid_mesh.faces_centers[:, 0], lid_mesh.faces_centers[:, 1]))


def test_lid_non_simply_connected_crown():
    pygmsh = pytest.importorskip("pygmsh")
    from capytaine.io.meshio import load_from_meshio
    with pygmsh.occ.Geometry() as geom:
        geom.add_torus((0, 0, 0), 2.0, 0.5, mesh_size=0.3)
        gmsh_mesh = geom.generate_mesh(dim=2)
    mesh = load_from_meshio(gmsh_mesh).immersed_part().heal_mesh()
    lid_mesh = mesh.generate_lid()
    def in_crown(x, y):
        return (np.hypot(x, y) < 2.5) & (np.hypot(x, y) > 1.5)
    assert all(in_crown(lid_mesh.faces_centers[:, 0], lid_mesh.faces_centers[:, 1]))


def test_lid_non_connex_crown():
    pygmsh = pytest.importorskip("pygmsh")
    from capytaine.io.meshio import load_from_meshio
    with pygmsh.occ.Geometry() as geom:
        geom.add_torus((0, 0, 0), 2.0, 0.5, mesh_size=0.4)
        gmsh_mesh = geom.generate_mesh(dim=2)
    mesh = load_from_meshio(gmsh_mesh).rotated_x(np.pi/2).immersed_part().heal_mesh()
    lid_mesh = mesh.generate_lid()
    def in_crown(x, y):
        return (np.hypot(x-2.0, y) < 0.5) | (np.hypot(x+2.0, y) < 0.5)
    assert all(in_crown(lid_mesh.faces_centers[:, 0], lid_mesh.faces_centers[:, 1]))


def test_lid_multibody():
    mesh = cpt.mesh_sphere(center=(0, 0, 0)) + cpt.mesh_sphere(center=(0, 5, 0))
    mesh = mesh.immersed_part()
    lid_mesh = mesh.generate_lid()
    def in_crown(x, y):
        return (np.hypot(x, y) < 1.0) | (np.hypot(x, y-5) < 1.0)
    assert all(in_crown(lid_mesh.faces_centers[:, 0], lid_mesh.faces_centers[:, 1]))


def test_lid_symmetric_mesh():
    mesh = cpt.mesh_vertical_cylinder(radius=1, reflection_symmetry=True).immersed_part()
    lid_mesh = mesh.generate_lid()
    assert isinstance(lid_mesh, cpt.ReflectionSymmetricMesh)
    def in_crown(x, y):
        return np.hypot(x, y) < 1.0
    assert all(in_crown(lid_mesh.faces_centers[:, 0], lid_mesh.faces_centers[:, 1]))


def test_lid_nested_symmetric_mesh():
    mesh = cpt.mesh_parallelepiped(reflection_symmetry=True).immersed_part()
    lid_mesh = mesh.generate_lid()
    assert isinstance(lid_mesh, cpt.ReflectionSymmetricMesh)
    assert isinstance(lid_mesh.half, cpt.ReflectionSymmetricMesh)
    def in_crown(x, y):
        return np.maximum(np.abs(x), np.abs(y)) < 0.5
    assert all(in_crown(lid_mesh.faces_centers[:, 0], lid_mesh.faces_centers[:, 1]))


def test_lid_auto_position():
    mesh = cpt.mesh_vertical_cylinder(radius=1.0).immersed_part()
    lid_mesh = mesh.generate_lid(z=mesh.lowest_lid_position(omega_max=5.0))
    body = cpt.FloatingBody(mesh=mesh, lid_mesh=lid_mesh)
    assert body.first_irregular_frequency_estimate() > 5.0


def test_lid_immersed_part():
    mesh = cpt.mesh_vertical_cylinder(radius=1.0).immersed_part()
    lid_mesh = mesh.generate_lid(z=0.0)
    assert lid_mesh.immersed_part().nb_faces > 0
    assert lid_mesh.immersed_part() == lid_mesh


def test_clipped_lid_above_the_free_surface():
    mesh = cpt.mesh_vertical_cylinder(radius=1.0).immersed_part()
    lid_mesh = mesh.generate_lid(z=0.5).immersed_part()
    body = cpt.FloatingBody(mesh=mesh, lid_mesh=lid_mesh)
    assert body.lid_mesh is None


def test_clipped_lid_above_the_free_surface__():
    mesh = cpt.mesh_vertical_cylinder(radius=1.0).immersed_part()
    lid_mesh = mesh.generate_lid(z=0.5)
    body = cpt.FloatingBody(mesh=mesh, lid_mesh=lid_mesh)
    body = body.immersed_part()
    assert body.lid_mesh is None


def test_lid_on_vertical_panels_only():
    # Used to raise an error.
    # https://github.com/capytaine/capytaine/issues/625
    mesh = cpt.mesh_rectangle(normal=(1, 0, 0))
    lid_mesh = mesh.generate_lid()


####################
#  Lid extraction  #
####################

def test_extract_lid():
    mesh = cpt.mesh_vertical_cylinder(center=(0, 0, -2), length=4, resolution=(2, 8, 10))
    hull_mesh, lid_mesh = mesh.extract_lid()
    assert lid_mesh.nb_faces == 2*8


def test_extract_lid_symmetric_mesh():
    mesh = cpt.mesh_vertical_cylinder(center=(0, 0, -2), length=4, resolution=(2, 8, 10), reflection_symmetry=True)
    hull_mesh, lid_mesh = mesh.extract_lid()
    assert isinstance(hull_mesh, cpt.ReflectionSymmetricMesh)
    assert isinstance(lid_mesh, cpt.ReflectionSymmetricMesh)


def test_extract_lid_nested_symmetric_mesh():
    mesh = cpt.mesh_parallelepiped(center=(0, 0, -1), reflection_symmetry=True)
    hull_mesh, lid_mesh = mesh.extract_lid()
    assert isinstance(hull_mesh, cpt.ReflectionSymmetricMesh)
    assert isinstance(hull_mesh.half, cpt.ReflectionSymmetricMesh)
    assert isinstance(lid_mesh, cpt.ReflectionSymmetricMesh)
    assert isinstance(lid_mesh.half, cpt.ReflectionSymmetricMesh)
