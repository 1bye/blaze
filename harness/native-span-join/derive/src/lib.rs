//! Verify that a native derive cannot join tokens originating in different files.
#![feature(proc_macro_span)]

extern crate proc_macro;

use proc_macro::{TokenStream, TokenTree};

/// Emits a marker constant after checking the item's cross-file spans.
#[proc_macro_derive(CrossFileJoin)]
pub fn cross_file_join(input: TokenStream) -> TokenStream {
    let mut tokens = input.into_iter();
    let keyword = tokens.next().expect("expected the struct keyword");
    let Some(TokenTree::Ident(name)) = tokens.next() else {
        panic!("expected the struct name");
    };
    let first = keyword.span();
    let second = name.span();
    assert_ne!(first.file(), second.file(), "fixture needs two source files");
    assert!(first.join(second).is_none(), "cross-file join must return None");
    "const CROSS_FILE_JOIN: &str = \"None\";".parse().expect("valid marker constant")
}
