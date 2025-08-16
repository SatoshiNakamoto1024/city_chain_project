pub fn example_function() -> String {
    String::from("This is an example function in mobile_app library.")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_example_function() {
        assert_eq!(example_function(), "This is an example function in mobile_app library.");
    }
}
