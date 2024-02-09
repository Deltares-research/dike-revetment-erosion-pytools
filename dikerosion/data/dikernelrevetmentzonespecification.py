"""
 Copyright (C) Stichting Deltares 2024. All rights reserved.
 
 This file is part of the dikernel-python toolbox.
 
 This program is free software; you can redistribute it and/or modify it under the terms of
 the GNU Lesser General Public License as published by the Free Software Foundation; either
 version 3 of the License, or (at your option) any later version.
 
 This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 See the GNU Lesser General Public License for more details.
 
 You should have received a copy of the GNU Lesser General Public License along with this
 program; if not, see <https://www.gnu.org/licenses/>.
 
 All names, logos, and references to "Deltares" are registered trademarks of Stichting
 Deltares and remain full property of Stichting Deltares at all times. All rights reserved.
"""

from __future__ import annotations
from dikerosion.data.toplayertypes import TopLayerType
from dikerosion.data.calculationmethods import CalculationMethod
from dikerosion.data.dikernelinput import DikeSchematization
from dikerosion.data.dikerneloutputspecification import (
    OutputLocationSpecification,
    AsphaltOutputLocationSpecification,
)
from abc import ABC, abstractmethod
import numpy as numpy


class RevetmentZoneDefinition(ABC):
    def __init__(self):
        self.include_schematization_coordinates = False

    @abstractmethod
    def get_x_coordinates(self, dike_schematization: DikeSchematization) -> list[float]:
        return None


class HorizontalRevetmentZoneDefinition(RevetmentZoneDefinition):
    def __init__(
        self, x_min: float, x_max: float, dx_max: float = None, nx: int = None
    ) -> None:
        super().__init__()
        self.x_min: float = x_min
        self.x_max: float = x_max
        self.nx: int = nx
        self.dx_max: float = dx_max

    def get_x_coordinates(self, dike_schematizaion: DikeSchematization):
        if self.nx is not None:
            nx = self.nx
        else:
            nx = numpy.ceil((self.x_max - self.x_min) / self.dx_max).astype(int) + 1

        x_coordinates = numpy.linspace(self.x_min, self.x_max, nx)
        if self.include_schematization_coordinates and dike_schematizaion is not None:
            x_coordinates = numpy.union1d(
                x_coordinates,
                [
                    x
                    for x in dike_schematizaion.x_positions
                    if x < self.x_max and x > self.x_min
                ],
            )

        return x_coordinates


class VerticalRevetmentZoneDefinition(RevetmentZoneDefinition):
    def __init__(
        self, z_min: float, z_max: float, dz_max: float = None, nz: int = None
    ) -> None:
        super().__init__()
        self.z_min: float = z_min
        self.z_max: float = z_max
        self.nz: int = nz
        self.dz_max: float = dz_max

    def get_x_coordinates(
        self, dike_schematizaion: DikeSchematization, inner_slope: bool = False
    ):
        x_coordaintes = numpy.array(dike_schematizaion.x_positions)
        z_coordaintes = numpy.array(dike_schematizaion.z_positions)
        filter_mask = (
            x_coordaintes <= dike_schematizaion.outer_crest
            if not inner_slope
            else x_coordaintes >= dike_schematizaion.outer_crest
        )
        x_dike = numpy.array(x_coordaintes[filter_mask])
        z_dike = numpy.array(z_coordaintes[filter_mask])

        if self.nz is not None:
            nz = self.nz
        else:
            nz = numpy.ceil((self.z_max - self.z_min) / self.dz_max).astype(int) + 1

        z_output_coordinates = numpy.linspace(self.z_min, self.z_max, nz)
        x_output_coordinates = numpy.interp(
            z_output_coordinates,
            z_dike,
            x_dike,
        )

        if self.include_schematization_coordinates and dike_schematizaion is not None:
            z_filter = numpy.logical_and(z_dike <= self.z_max, z_dike >= self.z_min)
            x_output_coordinates = numpy.union1d(
                x_output_coordinates,
                x_dike[z_filter],
            )
        return x_output_coordinates


class RevetmentZoneSpecification(ABC):
    def __init__(
        self,
        zone_definition: RevetmentZoneDefinition,
        calculation_method: CalculationMethod,
        top_layer_type: TopLayerType,
    ) -> RevetmentZoneSpecification:
        self.calculation_method = calculation_method
        self.top_layer_type = top_layer_type
        self.zone_definition = zone_definition

    @abstractmethod
    def get_output_locations(
        self, dike_schematization: DikeSchematization
    ) -> list[OutputLocationSpecification]:
        return None


class AsphaltRevetmentZoneSpecification(RevetmentZoneSpecification):
    def __init__(
        self,
        zone_definition: RevetmentZoneDefinition,
        flexural_strength_asphalt: float,
        spring_constant_soil: float,
        upper_layer_thickness: float,
        upper_layer_stiffness_modulus: float,
    ) -> AsphaltRevetmentZoneSpecification:
        super().__init__(
            zone_definition,
            CalculationMethod.AsphaltWaveImpact,
            TopLayerType.WAB,
        )
        self.flexural_strength: float = flexural_strength_asphalt
        self.soil_elasticity: float = spring_constant_soil
        self.upper_layer_thickness: float = upper_layer_thickness
        self.upper_layer_elastic_modulus: float = upper_layer_stiffness_modulus
        self.sub_layer_thickness: float = None
        self.sub_layer_elastic_modulus: float = None
        self.fatigue_alpha: float = None
        self.fatigue_beta: float = None
        self.top_layer_stiffness_relation_nu: float = None

    def get_output_locations(
        self, dike_schematization: DikeSchematization
    ) -> list[AsphaltOutputLocationSpecification]:
        locations = []
        x_output_locations = self.zone_definition.get_x_coordinates(dike_schematization)
        for x_output_location in x_output_locations:
            locations.append(
                AsphaltOutputLocationSpecification(
                    x_output_location,
                    self.flexural_strength,
                    self.soil_elasticity,
                    self.upper_layer_thickness,
                    self.upper_layer_elastic_modulus,
                )
            )

        return locations
