//! The smallest function-like proc macro that changes an expression's string value.
use proc_macro::TokenStream;

#[proc_macro]
pub fn screen(input: TokenStream) -> TokenStream {
    input
}
