use serde_json::Value;

use crate::{
    footprint::Footprint,
    metapart::{Metapart, Specs},
};

pub struct SmdCapacitor {
    value: String,
    footprint: Footprint,
    tolerance: Option<String>,
    voltage_rating: Option<String>,
    dielectric_type: Option<String>,
}

impl SmdCapacitor {
    pub fn new(value: String, footprint: Footprint) -> Self {
        Self {
            value,
            footprint,
            tolerance: None,
            voltage_rating: None,
            dielectric_type: None,
        }
    }

    pub fn with_full_specs(
        self,
        tolerance: String,
        voltage_rating: String,
        dielectric_type: String,
    ) -> Self {
        Self {
            tolerance: Some(tolerance),
            voltage_rating: Some(voltage_rating),
            dielectric_type: Some(dielectric_type),
            ..self
        }
    }
}

impl Metapart for SmdCapacitor {
    const TYPE: &str = "Capacitor";
    const DESIGNATOR: &str = "C";

    fn footprint(&self) -> Footprint {
        self.footprint
    }

    fn kicad_footprint(&self) -> &str {
        match self.footprint {
            Footprint::Smd0201 => "Capacitor_SMD:C_0201_0603Metric",
            Footprint::Smd0402 => "Capacitor_SMD:C_0402_1005Metric",
            Footprint::Smd0603 => "Capacitor_SMD:C_0603_1608Metric",
            Footprint::Smd0805 => "Capacitor_SMD:C_0805_2012Metric",
            Footprint::Smd1206 => "Capacitor_SMD:C_1206_3216Metric",
        }
    }

    fn kicad_symbol(&self) -> &str {
        "Device:C"
    }

    fn specs(&self) -> Specs {
        let mut name = format!("{}-{}-{}", Self::DESIGNATOR, self.value, self.footprint);
        let mut description = format!("{}, {}, {}", Self::TYPE, self.value, self.footprint);
        if let (Some(tol), Some(voltage), Some(dielectric)) =
            (&self.tolerance, &self.voltage_rating, &self.dielectric_type)
        {
            name = format!("{name}-{tol}-{voltage}-{dielectric}");
            description = format!("{description}, ±{tol}, {voltage}, {dielectric}");
        }

        Specs {
            value: self.value.clone(),
            name,
            description,
        }
    }

    fn extra_tags(&self) -> Vec<Value> {
        let mut tags = vec![Value::String("SMD".to_owned())];
        if let Some(dielectric) = &self.dielectric_type {
            tags.push(Value::String(dielectric.clone()));
        }
        tags
    }

    fn extra_custom_fields(&self) -> Vec<Value> {
        let mut fields = Vec::new();

        if let Some(tol) = &self.tolerance {
            fields.push(serde_json::json!({
                "key": "tolerance",
                "value": tol
            }));
        }

        if let Some(voltage) = &self.voltage_rating {
            fields.push(serde_json::json!({
                "key": "voltage_rating",
                "value": voltage
            }));
        }

        if let Some(dielectric) = &self.dielectric_type {
            fields.push(serde_json::json!({
                "key": "dielectric_type",
                "value": dielectric
            }));
        }

        fields
    }
}
