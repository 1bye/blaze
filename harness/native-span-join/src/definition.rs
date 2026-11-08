macro_rules! define_probe {
    ($name:ident) => {
        #[derive(span_join_derive::CrossFileJoin)]
        struct $name;
    };
}
