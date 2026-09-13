create table if not exists public.conteudos (
    id serial primary key,
    slug varchar(50) unique not null,
    titulo varchar(150) not null,
    texto text not null
);