fn greet(name: &str) -> String {
    format!("Helllo, {name}!")
}

fn main() {
    println!("{}", greet("world"));
}
