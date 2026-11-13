pub fn result() -> u64 {
    #[cfg(feature = "devtools")]
    {
        let mut h = hdrhistogram::Histogram::<u64>::new(3).unwrap();
        h.record(7).unwrap();
        h.max()
    }
    #[cfg(not(feature = "devtools"))]
    {
        0
    }
}
