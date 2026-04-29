use crate::footprint::Footprint;
use serde_json::Value;

pub mod resistor;
pub use resistor::*;

pub mod capacitor;
pub use capacitor::*;

pub struct Specs {
    name: String,
    description: String,
    value: String,
}

impl Specs {
    pub fn name(&self) -> &str {
        &self.name
    }
}

pub trait Metapart {
    const TYPE: &str;
    const DESIGNATOR: &str;

    fn footprint(&self) -> Footprint;
    fn specs(&self) -> Specs;
    fn kicad_footprint(&self) -> &str;
    fn kicad_symbol(&self) -> &str;

    fn extra_tags(&self) -> Vec<Value> {
        Vec::new()
    }

    fn extra_custom_fields(&self) -> Vec<Value> {
        Vec::new()
    }

    fn create_payload(&self) -> Value {
        let specs = self.specs();
        let footprint = self.footprint();

        let mut custom_fields = vec![serde_json::json!({ "key": "value", "value": specs.value })];
        custom_fields.extend(self.extra_custom_fields());

        let mut tags = vec![
            Value::String(Self::TYPE.to_lowercase()),
            Value::String(footprint.to_string()),
        ];
        tags.extend(self.extra_tags());

        serde_json::json!({
            "part/name": specs.name,
            "part/type": "meta",
            "part/description": specs.description,
            "part/tags": tags,
            "part/footprint": footprint,
            "part/kicad-symbol": self.kicad_symbol(),
            "part/kicad-reference": Self::DESIGNATOR,
            "part/kicad-footprint": self.kicad_footprint(),
            "part/custom-fields": custom_fields,
        })
    }
}
