//! GPUI/accesskit_macos (#1259): objc2's C callbacks return an associated-type
//! projection. Layout resolved it, but aggregate field classification inspected the alias.

use std::hint::black_box;

#[repr(C)]
#[derive(Clone, Copy)]
struct Quad {
    a: f64,
    b: f64,
    c: f64,
    d: f64,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct Triple {
    a: f32,
    b: f32,
    c: f32,
}

trait Legacy {
    type __Inner;
}
trait Modern<Marker> {
    type Inner;
}
impl Legacy for Quad {
    type __Inner = Self;
}
impl Legacy for Triple {
    type __Inner = Self;
}
impl Modern<()> for Quad {
    type Inner = Self;
}

#[repr(C)]
#[derive(Clone, Copy)]
struct Nested {
    value: <Triple as Legacy>::__Inner,
}

#[inline(never)]
extern "C" fn legacy(value: <Quad as Legacy>::__Inner) -> <Quad as Legacy>::__Inner {
    value
}

#[inline(never)]
extern "C" fn modern(value: <Quad as Modern<()>>::Inner) -> <Quad as Modern<()>>::Inner {
    value
}

#[inline(never)]
extern "C" fn nested(value: Nested) -> Nested {
    value
}

fn bits(value: Quad) -> [u64; 4] {
    [value.a.to_bits(), value.b.to_bits(), value.c.to_bits(), value.d.to_bits()]
}

pub fn run() -> ([u64; 4], [u64; 4], [u32; 3]) {
    let value = black_box(Quad {
        a: f64::from_bits(0x7ff8_0000_0000_0042),
        b: -0.0,
        c: f64::INFINITY,
        d: f64::from_bits(1),
    });
    let old: extern "C" fn(Quad) -> Quad = legacy;
    let new: extern "C" fn(Quad) -> Quad = modern;
    let inner = nested(black_box(Nested { value: Triple { a: 1.25, b: -2.5, c: 3.75 } }));
    (
        bits(old(value)),
        bits(new(value)),
        [inner.value.a.to_bits(), inner.value.b.to_bits(), inner.value.c.to_bits()],
    )
}
