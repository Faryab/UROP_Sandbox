from sys import platform as sys_pf
if sys_pf == 'darwin':
    import matplotlib
    matplotlib.use("TkAgg")

# for above refer to:
# https://github.com/MTG/sms-tools/issues/36

import openmc, sys
FREECADPATH = '/Users/faryab/anaconda3/envs/UROPTesting/lib'
sys.path.append(FREECADPATH)
import FreeCAD

# Have to import FREECAD from a separate env into this one.
# in order to have FREECAD actually work, make sure you have
# Python  3.6.0 or 3.6.2 (3.6.7 DOES NOT work and results
# in a seg fault) I have not tested it with 3.6.3-3.3.6 so far.

##### Modelling a Pin Cell ###

## Defining Materials
uo2 = openmc.Material(1, "uo2")

mat = openmc.Material()
# Add nuclides to uo2
uo2.add_nuclide('U235', 0.03)
uo2.add_nuclide('U238', 0.97)
uo2.add_nuclide('O16', 2.0)

uo2.set_density('g/cm3', 10.0)

zirconium = openmc.Material(2, "zirconium")
zirconium.add_element('Zr', 1.0)
zirconium.set_density('g/cm3', 6.6)

water = openmc.Material(3, "h2o")
water.add_nuclide('H1', 2.0)
water.add_nuclide('O16', 1.0)
water.set_density('g/cm3', 1.0)

water.add_s_alpha_beta('c_H_in_H2O')

mats = openmc.Materials([uo2, zirconium, water])

mats = openmc.Materials()
mats.append(uo2)
mats += [zirconium, water]

mats.export_to_xml()

## Element Expansion

water.remove_nuclide('O16')
water.add_element('O', 1.0)

mats.export_to_xml()

## Enrichment

uo2_three = openmc.Material()
uo2_three.add_element('U', 1.0, enrichment=3.0)
uo2_three.add_element('O', 2.0)
uo2_three.set_density('g/cc', 10.0)

## Defining Geometry

sph = openmc.Sphere(R=1.0)

inside_sphere = -sph
outside_sphere = +sph

z_plane = openmc.ZPlane(z0=0)
northern_hemisphere = -sph & +z_plane

northern_hemisphere.bounding_box

cell = openmc.Cell()
cell.region = northern_hemisphere

cell.fill = water

## Universes and in-line plotting

universe = openmc.Universe()
universe.add_cell(cell)

# universe.plot(width=(2.0, 2.0))
# universe.plot(width=(2.0, 2.0), basis='xz')
# universe.plot(width=(2.0, 2.0), basis='xz', colors={cell: 'fuchsia'})

## Pin cell geometry

# Modifications
z_top = openmc.ZPlane(z0=0.5, boundary_type='reflective')
z_bot = openmc.ZPlane(z0=-0.5, boundary_type='reflective')

fuel_or = openmc.ZCylinder(R=0.39)
clad_ir = openmc.ZCylinder(R=0.40)
clad_or = openmc.ZCylinder(R=0.46)

fuel_region = -fuel_or & +z_bot & -z_top
gap_region = +fuel_or & -clad_ir & +z_bot & -z_top
clad_region = +clad_ir & -clad_or & +z_bot & -z_top

fuel = openmc.Cell(1, 'fuel')
fuel.fill = uo2
fuel.region = fuel_region

gap = openmc.Cell(2, 'air gap')
gap.region = gap_region

clad = openmc.Cell(3, 'clad')
clad.fill = zirconium
clad.region = clad_region

pitch = 1.26
left = openmc.XPlane(x0=-pitch/2, boundary_type='reflective')
right = openmc.XPlane(x0=pitch/2, boundary_type='reflective')
bottom = openmc.YPlane(y0=-pitch/2, boundary_type='reflective')
top = openmc.YPlane(y0=pitch/2, boundary_type='reflective')


water_region = +left & -right & +bottom & -top & +clad_or & -z_top & +z_bot

moderator = openmc.Cell(4, 'moderator')
moderator.fill = water
moderator.region = water_region

#box = openmc.get_rectangular_prism(width=pitch, height=pitch, boundary_type='reflective')
#water_region = box & +clad_or

root = openmc.Universe(cells=(fuel, gap, clad, moderator))
geom = openmc.Geometry(root)
geom.export_to_xml()


## Starting source and settings

point = openmc.stats.Point((0, 0, 0))
src = openmc.Source(space=point)

settings = openmc.Settings()
settings.source = src
settings.batches = 100
settings.inactive = 10
settings.particles = 1000

settings.export_to_xml()

# User-defined tallies

cell_filter = openmc.CellFilter(fuel)

t = openmc.Tally(1)
t.filters = [cell_filter]

t.nuclides = ['U235']
t.scores = ['total', 'fission', 'absorption', '(n,gamma)']

tallies = openmc.Tallies([t])
tallies.export_to_xml()

# Running OpenMC¶
# openmc.run()
# FIX: For some reason not working on pycharm,
# yet works fine on iPython