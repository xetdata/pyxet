use std::process::Command;
fn main() {
    println!("cargo:rerun-if-changed=hooks/*");
    Command::new("bash")
        .args(&["build_hooks.sh"])
        .status()
        .unwrap();
}
