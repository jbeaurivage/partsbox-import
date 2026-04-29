use crate::{
    footprint::Footprint,
    metapart,
    partsbox_api::{Client, PartId},
};

#[derive(Clone, Debug)]
pub struct SmdResistor {
    mpn: String,
    id: PartId,
    value: String,
    footprint: Footprint,
    tolerance: String,
    power_rating: String,
}

impl SmdResistor {
    pub fn new(
        mpn: impl AsRef<str>,
        id: &PartId,
        value: impl AsRef<str>,
        footprint: &Footprint,
        tolerance: impl AsRef<str>,
        power_rating: impl AsRef<str>,
    ) -> Self {
        Self {
            mpn: mpn.as_ref().to_string(),
            id: id.clone(),
            value: value.as_ref().to_string(),
            footprint: *footprint,
            tolerance: tolerance.as_ref().to_string(),
            power_rating: power_rating.as_ref().to_string(),
        }
    }

    pub fn into_partial_metapart(self) -> metapart::SmdResistor {
        metapart::SmdResistor::new(self.value, self.footprint)
    }

    pub fn into_full_metapart(self) -> metapart::SmdResistor {
        let tolerance = self.tolerance.clone();
        let power_rating = self.power_rating.clone();

        self.into_partial_metapart()
            .with_full_specs(tolerance, power_rating)
    }
}

#[derive(Clone, Debug)]
pub struct SmdCapacitor {
    mpn: String,
    id: PartId,
    value: String,
    footprint: Footprint,
    tolerance: String,
    voltage_rating: String,
    dielectric_type: String,
}

impl SmdCapacitor {
    pub fn new(
        mpn: impl AsRef<str>,
        id: &PartId,
        value: impl AsRef<str>,
        footprint: &Footprint,
        tolerance: impl AsRef<str>,
        voltage_rating: impl AsRef<str>,
        dielectric_type: impl AsRef<str>,
    ) -> Self {
        Self {
            mpn: mpn.as_ref().to_string(),
            id: id.clone(),
            value: value.as_ref().to_string(),
            footprint: *footprint,
            tolerance: tolerance.as_ref().to_string(),
            voltage_rating: voltage_rating.as_ref().to_string(),
            dielectric_type: dielectric_type.as_ref().to_string(),
        }
    }

    pub fn into_partial_metapart(self) -> metapart::SmdCapacitor {
        metapart::SmdCapacitor::new(self.value, self.footprint)
    }

    pub fn into_full_metapart(self) -> metapart::SmdCapacitor {
        let tolerance = self.tolerance.clone();
        let voltage_rating = self.voltage_rating.clone();
        let dielectric_type = self.dielectric_type.clone();

        self.into_partial_metapart()
            .with_full_specs(tolerance, voltage_rating, dielectric_type)
    }
}
