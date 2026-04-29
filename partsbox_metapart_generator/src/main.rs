use std::{fs::File, io::BufReader, path::Path};

use partsbox_metapart_generator::{
    concrete_part,
    footprint::Footprint,
    metapart::Metapart,
    partsbox_api::{self, PartId},
};

fn main() -> anyhow::Result<()> {
    let mut client = partsbox_api::Client::new()?;

    // let all_parts = api.all_parts()?;
    // println!("{}", serde_json::to_string(&all_parts)?);

    // Open the file in read-only mode with buffer.
    let path = Path::new("../metaparts/lcsc.json");
    let file = File::open(path)?;
    let reader = BufReader::new(file);

    let parts: serde_json::Value = serde_json::from_reader(reader)?;
    let parts = parts
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("Expected part_specs.json to contain a JSON array"))?;

    for part in parts {
        let Some(specs) = part.get("specs") else {
            continue;
        };

        let Some(part_type) = specs.get("type").and_then(|v| v.as_str()) else {
            continue;
        };

        let id = PartId::new(get_str(part, "part/id")?);
        let mpn = get_str(part, "part/mpn")?;

        if part_type == "resistor" {
            let value = get_str(specs, "resistance")?;
            let tolerance = get_str(specs, "tolerance")?;
            let power_rating = get_str(specs, "power_rating")?;
            let footprint = Footprint::parse(get_str(specs, "footprint")?)?;

            let part = concrete_part::SmdResistor::new(
                mpn,
                &id,
                value,
                &footprint,
                tolerance,
                power_rating,
            );

            let partial_metapart = part.clone().into_partial_metapart();
            let partial_metapart_id = client.create_part(&partial_metapart.create_payload())?;
            if client
                .add_metapart_ids(&partial_metapart_id, &[&id])
                .is_err()
            {
                println!(
                    "WARN: metapart already exists: ID {}, name: {}",
                    partial_metapart_id.id(),
                    partial_metapart.specs().name()
                )
            } else {
                println!(
                    "Added metapart: ID {}, name: {}",
                    partial_metapart_id.id(),
                    partial_metapart.specs().name()
                )
            }

            let full_metapart = part.clone().into_full_metapart();
            let full_metapart_id = client.create_part(&full_metapart.create_payload())?;
            if client.add_metapart_ids(&full_metapart_id, &[&id]).is_err() {
                println!(
                    "WARN: metapart already exists: ID {}, name: {}",
                    full_metapart_id.id(),
                    full_metapart.specs().name()
                )
            } else {
                println!(
                    "Added metapart: ID {}, name: {}",
                    full_metapart_id.id(),
                    full_metapart.specs().name()
                )
            }
        } else if part_type == "capacitor" {
            let value = get_str(specs, "capacitance")?;
            let tolerance = get_str(specs, "tolerance")?;
            let footprint = Footprint::parse(get_str(specs, "footprint")?)?;
            let voltage_rating = get_str(specs, "voltage_rating")?;
            let dielectric_type = get_str(specs, "dielectric")?;

            let part = concrete_part::SmdCapacitor::new(
                mpn,
                &id,
                value,
                &footprint,
                tolerance,
                voltage_rating,
                dielectric_type,
            );

            let partial_metapart = part.clone().into_partial_metapart();
            let partial_metapart_id = client.create_part(&partial_metapart.create_payload())?;
            if client
                .add_metapart_ids(&partial_metapart_id, &[&id])
                .is_err()
            {
                println!(
                    "WARN: metapart already exists: ID {}, name: {}",
                    partial_metapart_id.id(),
                    partial_metapart.specs().name()
                )
            } else {
                println!(
                    "Added metapart: ID {}, name: {}",
                    partial_metapart_id.id(),
                    partial_metapart.specs().name()
                )
            }

            let full_metapart = part.clone().into_full_metapart();
            let full_metapart_id = client.create_part(&full_metapart.create_payload())?;
            if client.add_metapart_ids(&full_metapart_id, &[&id]).is_err() {
                println!(
                    "WARN: metapart already exists: ID {}, name: {}",
                    full_metapart_id.id(),
                    full_metapart.specs().name()
                )
            } else {
                println!(
                    "Added metapart: ID {}, name: {}",
                    full_metapart_id.id(),
                    full_metapart.specs().name()
                )
            }
        }
    }

    Ok(())
}

fn get_str<'a>(val: &'a serde_json::Value, key: &str) -> anyhow::Result<&'a str> {
    val.get(key)
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("Could not get key: {key} for value: {val}"))
}
