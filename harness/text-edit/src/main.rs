//! Differential values and source locations after string-only edits.
use text_edit_macros::screen;

#[track_caller]
fn tracked() -> String {
    let at = std::panic::Location::caller();
    format!("{}:{}:{}", at.file(), at.line(), at.column())
}

fn render() -> String {
    let title = screen!("text-one");
    format!("{}|{}|{}|{}", title, tracked(), [0u8; "const-one".len()].len(), b"bytes-one".len())
}
fn boom() {
    let _ = screen!("panic-one");
    panic!("text-edit-probe");
}

fn main() {
    println!("RESULT:{}", render());
    if std::env::args().any(|arg| arg == "panic") {
        std::panic::set_hook(Box::new(|info| {
            let at = info.location().expect("explicit panic has a location");
            println!("PANIC:{}:{}:{}", at.file(), at.line(), at.column());
        }));
        boom();
    }
}
