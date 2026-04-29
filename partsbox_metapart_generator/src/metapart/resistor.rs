use serde_json::Value;

use crate::{
    footprint::Footprint,
    metapart::{Metapart, Specs},
};

pub struct SmdResistor {
    value: String,
    footprint: Footprint,
    tolerance: Option<String>,
    power_rating: Option<String>,
}

impl SmdResistor {
    pub fn new(value: String, footprint: Footprint) -> Self {
        Self {
            value,
            footprint,
            tolerance: None,
            power_rating: None,
        }
    }

    pub fn with_full_specs(self, tolerance: String, power_rating: String) -> Self {
        Self {
            tolerance: Some(tolerance),
            power_rating: Some(power_rating),
            ..self
        }
    }
}

impl Metapart for SmdResistor {
    const TYPE: &str = "Resistor";
    const DESIGNATOR: &str = "R";

    fn footprint(&self) -> Footprint {
        self.footprint
    }

    fn kicad_footprint(&self) -> &str {
        match self.footprint {
            Footprint::Smd0201 => "Resistor_SMD:R_0201_0603Metric",
            Footprint::Smd0402 => "Resistor_SMD:R_0402_1005Metric",
            Footprint::Smd0603 => "Resistor_SMD:R_0603_1608Metric",
            Footprint::Smd0805 => "Resistor_SMD:R_0805_2012Metric",
            Footprint::Smd1206 => "Resistor_SMD:R_1206_3216Metric",
        }
    }

    fn kicad_symbol(&self) -> &str {
        "Device:R"
    }

    fn specs(&self) -> Specs {
        let mut name = format!("{}-{}-{}", Self::DESIGNATOR, self.value, self.footprint);
        let mut description = format!("{}, {}, {}", Self::TYPE, self.value, self.footprint);
        if let (Some(tol), Some(pwr)) = (&self.tolerance, &self.power_rating) {
            name = format!("{name}-{tol}-{pwr}");
            description = format!("{description}, ±{tol}, {pwr}");
        }

        Specs {
            value: self.value.clone(),
            name,
            description,
        }
    }

    fn extra_tags(&self) -> Vec<Value> {
        vec![Value::String("SMD".to_owned())]
    }

    fn extra_custom_fields(&self) -> Vec<Value> {
        let mut fields = Vec::new();

        if let Some(tol) = &self.tolerance {
            fields.push(serde_json::json!({
                "key": "tolerance",
                "value": tol
            }));
        }

        if let Some(pwr) = &self.power_rating {
            fields.push(serde_json::json!({
                "key": "power_rating",
                "value": pwr
            }));
        }

        fields
    }
}
