use actix_web::{web, App, HttpResponse, HttpRequest, HttpServer, Responder};
use actix_web::body::BoxBody;

struct MyResponse {
    message: String,
}

impl Responder for MyResponse {
    type Body = BoxBody;  // <-- обязательно указываем связанный тип

    fn respond_to(self, _req: &HttpRequest) -> HttpResponse<Self::Body> {
        HttpResponse::Ok()
            .content_type("vmlx/data; charset=utf-8")
            .body(self.message)
    }
}
async fn index() -> impl Responder {
    MyResponse {
        message: "Hello from MyResponse!".to_string(),
    }
}


#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/", web::post().to(index)) // Регистрируем маршрут
    })
    .bind("127.0.0.1:8080")? // Слушаем порт 8080
    .run()
    .await
}