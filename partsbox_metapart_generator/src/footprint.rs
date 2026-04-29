use std::fmt::Display;

use serde::Serialize;

#[derive(Debug, Clone, Copy)]
pub enum Footprint {
    Smd0201,
    Smd0402,
    Smd0603,
    Smd0805,
    Smd1206,
}

impl Footprint {
    pub fn canonical_name(&self) -> &'static str {
        match self {
            Footprint::Smd0201 => "0201",
            Footprint::Smd0402 => "0402",
            Footprint::Smd0603 => "0603",
            Footprint::Smd0805 => "0805",
            Footprint::Smd1206 => "1206",
        }
    }

    pub fn parse(footprint: impl AsRef<str>) -> anyhow::Result<Self> {
        let footprint = footprint.as_ref();
        match footprint {
            "0201" => Ok(Footprint::Smd0201),
            "0402" => Ok(Footprint::Smd0402),
            "0603" => Ok(Footprint::Smd0603),
            "0805" => Ok(Footprint::Smd0805),
            "1206" => Ok(Footprint::Smd1206),
            _ => Err(anyhow::anyhow!("Could not match footprit: {footprint}")),
        }
    }
}

impl Serialize for Footprint {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(self.canonical_name())
    }
}

impl Display for Footprint {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.canonical_name())
    }
}
