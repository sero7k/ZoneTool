//! bo2mp: images a map's materials use that the zone neither embeds nor streams (0x0, "," names: defined elsewhere),
//! with the pack name hash `ipak_pull.ps1` takes. `t6_missing_images <zone.ff>`
fn main() {
    let path = std::env::args().nth(1).expect("zone");
    let c = asset_t6::capture_zone(std::path::Path::new(&path)).expect("capture");
    let mut seen = std::collections::BTreeMap::new();
    for m in &c.materials {
        for t in &m.textures {
            if let Some(i) = t.image.and_then(|k| c.images.get(k.index)) {
                if i.width == 0 && i.embedded.is_none() {
                    seen.entry(i.name.clone()).or_insert_with(Vec::new).push(format!("{}:{}", t.semantic, m.name));
                }
            }
        }
    }
    let mut hashes = Vec::new();
    for (n, users) in &seen {
        let h = ipak_t6::hash_name(n.trim_start_matches(','));
        hashes.push(h.to_string());
        println!("{h} {n} <- {}", users.join(" "));
    }
    println!("hashes {}", hashes.join(","));
}
