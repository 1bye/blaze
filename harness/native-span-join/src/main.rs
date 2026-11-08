#[macro_use]
mod definition;

define_probe!(Probe);

fn main() {
    let _ = Probe;
    println!("cross-file join: {CROSS_FILE_JOIN}");
}
