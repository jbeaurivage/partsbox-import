use std::fmt::Display;

use reqwest::{blocking::ClientBuilder, header::HeaderMap};
use serde::Serialize;

#[derive(Debug, Clone, serde::Serialize)]
pub struct PartId(String);

impl PartId {
    pub fn new(id: impl AsRef<str>) -> Self {
        Self(id.as_ref().to_owned())
    }

    pub fn id(&self) -> &str {
        &self.0
    }
}

pub struct Client {
    client: reqwest::blocking::Client,
}

impl Client {
    pub fn new() -> anyhow::Result<Self> {
        let api_key = dotenv::var("PARTSBOX_API_KEY")?;
        Self::new_with_key(api_key)
    }

    pub fn new_with_key(api_key: impl AsRef<str> + Display) -> anyhow::Result<Self> {
        let mut headers = HeaderMap::new();
        headers.insert("Authorization", format!("APIKey {api_key}").parse()?);

        let client = ClientBuilder::new()
            .default_headers(headers)
            .build()
            .unwrap();
        Ok(Self { client })
    }

    pub fn all_parts(&mut self) -> anyhow::Result<serde_json::Value> {
        const PATH: &str = "part/all";
        let response = self.post(PATH, &serde_json::json!({}))?;

        let response = response
            .get("data")
            .ok_or_else(|| anyhow::anyhow!("Invalid response"))?;
        Ok(response.clone())
    }

    pub fn find_part_id_by_name(&mut self, name: &str) -> anyhow::Result<Option<PartId>> {
        let parts = self.all_parts()?;
        let parts = parts.as_array().ok_or_else(|| {
            anyhow::anyhow!("Invalid response: expected data array from part/all")
        })?;

        for part in parts {
            let part_name = part.get("part/name").and_then(|v| v.as_str());
            if part_name == Some(name) {
                let id = part
                    .get("part/id")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| anyhow::anyhow!("Found matching part without string part/id"))?;
                return Ok(Some(PartId::new(id)));
            }
        }

        Ok(None)
    }

    pub fn create_part<P: Serialize + ?Sized>(&mut self, payload: &P) -> anyhow::Result<PartId> {
        const PATH: &str = "part/create";

        let payload_value = serde_json::to_value(payload)?;
        if let Some(name) = payload_value.get("part/name").and_then(|v| v.as_str())
            && let Some(existing_id) = self.find_part_id_by_name(name)?
        {
            println!(
                "Part already exists: ID {}, name: {}",
                existing_id.id(),
                name
            );
            return Ok(existing_id);
        }

        let response = self.post(PATH, payload)?;
        let response = response
            .get("data")
            .ok_or_else(|| anyhow::anyhow!("Invalid response"))?
            .get("part/id")
            .ok_or_else(|| anyhow::anyhow!("Created part ID not found"))?;

        let id = response
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("part/id was not a JSON string"))?;

        Ok(PartId(id.to_owned()))
    }

    pub fn add_metapart_ids(
        &mut self,
        metapart_id: &PartId,
        member_ids: &[&PartId],
    ) -> anyhow::Result<()> {
        self.post(
            "part/add-meta-part-ids",
            &serde_json::json!({"part/id": metapart_id.id(), "part/part-ids": member_ids}),
        )?;

        Ok(())
    }

    pub(crate) fn post<P: Serialize + ?Sized>(
        &mut self,
        path: &str,
        payload: &P,
    ) -> anyhow::Result<serde_json::Value> {
        const BASE_URL: &str = "https://api.partsbox.com/api/1";
        // const BASE_URL: &str = "https://partsbox.free.beeceptor.com";
        let path = format!("{BASE_URL}/{path}");

        let response = self.client.post(path).json(payload).send()?.text()?;
        // println!("{}", response);
        let response = serde_json::from_str(&response)?;
        Ok(response)
    }
}
