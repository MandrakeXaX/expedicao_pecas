-- Execute no SQL Editor do Supabase. Mantenha a service_role key somente no servidor.
create table if not exists public.volumes (
 id bigint generated always as identity primary key,
 pedido text not null,
 volume integer not null check(volume > 0),
 total_volumes integer not null check(total_volumes > 0),
 tipo text not null default 'Garantia' check(tipo in ('Garantia','Venda')),
 codigos text not null,
 data_pedido date not null,
 status text not null default 'Pendente' check(status in ('Pendente','Expedido')),
 expedido_em timestamptz,
 foto_path text,
 operador text,
 criado_em timestamptz not null default now(),
 unique(pedido, volume),
 check(volume <= total_volumes)
);
create index if not exists volumes_status_idx on public.volumes(status, data_pedido);
alter table public.volumes enable row level security;
-- Nenhuma política pública: somente a service_role do servidor acessa os dados.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('fotos-expedicao','fotos-expedicao',false,10485760,array['image/jpeg','image/png'])
on conflict(id) do nothing;
create or replace function public.registrar_expedicao(p_pedido text,p_volume integer,p_foto_path text,p_operador text)
returns public.volumes language plpgsql security invoker as $$
declare v public.volumes;
begin
 update public.volumes set status='Expedido', expedido_em=now(), foto_path=p_foto_path, operador=p_operador
 where pedido=p_pedido and volume=p_volume and status='Pendente'
 returning * into v;
 if not found then raise exception 'Volume não encontrado ou já expedido'; end if;
 return v;
end $$;
-- Execute UMA VEZ no SQL Editor do seu projeto Supabase antes de usar a atualização.
-- Adiciona campos sem excluir pedidos ou fotos existentes.
alter table public.volumes add column if not exists ordem_servico text;
alter table public.volumes add column if not exists nome_cliente text;
alter table public.volumes add column if not exists peso_bruto numeric;
notify pgrst, 'reload schema';
