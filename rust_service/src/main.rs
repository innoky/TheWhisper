fn test(s: &String) -> String
{
    s = String::from("hell");
    s
}

fn main()
{
    let s = String::from("hello");
    let b = test(&s);
    println!("{}",b);
}