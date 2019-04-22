import math


class MeshParams:
    """
    Parameters for a Mesh (for a Geometry)
    """
    def __init__(self, nrad=1):
        self.nRad = nrad


class Geom:
    """
    A Geometry object (an attribute of a Level). Can be any elementary shape. Sub-Classes
    devolve into the different shapes possible.
    """
    def __init__(self, name=None):
        self.Name = name


class CircleGeom(Geom):
    """
    Inherits from Geom. Defines a Circle in MPACT.
    """
    def __init__(self, r=0, centroid=(0,0), startangl=0.0, stopangl=2*math.pi, meshparams=None):
        Geom.__init__(self)
        self.Name = "CircleGeom"
        self.Radius = r
        self.Centroid = centroid  # the circles center
        self.StartAngle = startangl  # where the circle starts (anticlockwise) 0 = 1st quadrant +x-axis
        self.StopAngle = stopangl  # where the circle stops (anticlockwise) pi = 2nd quadrant -x axis
        self.MeshParams = meshparams
        # TODO: Should Mesh Params be a list? Yes. There are different parameters (e.g. for box brendan will send)


class BoxGeom(Geom):
    """
    Inherits from Geom. Defines a Box (quadrilateral) in MPACT.
    """
    # TODO: Ask Brendan about Squares again done
    def __init__(self, cornerpt=(0,0), vector1=None, vector2=None, extent=None, meshparams=None):
        Geom.__init__(self)
        self.Name = "BoxGeom"
        self.CornerPoint = cornerpt
        self.Vector1 = [1, 0] if vector1 is None else vector1
        self.Vector2 = [0, 1] if vector2 is None else vector2
        self.Extent = extent
        self.MeshParams = meshparams
        # TODO: Should Mesh Params be a list? done


class Level:
    """
    Attribute of a GeneralMeshType Object. Contains a geometry as a sub-object on a
    specific level. Each level can have different numbers of geometries (for now we
    assume each level will only have a single geometry). Each level itself is unique
    """
    def __index__(self, ngeom=0, geoms=None, name=None):
        self.name = name  # The level number
        self.nGeom = ngeom
        self.geoms = [] if geoms is None else geoms

    def add_geom(self, geom):
        if geom in self.geoms:
            print("Error: Geometry is already in the list of geometries for this level.")
        else:
            self.geoms.append(geom)
            self.nGeom += 1


class GeneralMeshType:
    """
    General Mesh Type class for defining MPACT Geometry. Contains the entire geomety as its
    sub-objects. Acts as the root of the XML tree.
    """
    def __init__(self, name="GenPinMeshType", id=None, nlevels=0, xpitch=0.0,
                 ypitch=0.0, zpitch=0.0, split=0, levels=None):
        self.name = name
        self.ID = id
        self.NLevels = nlevels
        self.XPitch = xpitch
        self.YPitch = ypitch
        self.ZPitch = zpitch
        self.Split = split
        self.Levels = {} if levels is None else levels

    def add_level(self, level):
        if level.name in self.Levels:
            print("Error: Level Number already added")
            return
        else:
            self.Levels[level.name] = level
            self.NLevels += 1

    def remove_level(self, level_num):
        if level_num in self.Levels:
            print("Error: Specified level is not in the model")
            return
        else:
            del self.Levels[level_num]


