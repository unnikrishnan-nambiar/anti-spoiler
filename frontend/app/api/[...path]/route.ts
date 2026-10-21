import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
export const dynamic='force-dynamic';
const backend=process.env.BACKEND_URL || 'http://api:8000';
async function proxy(request:NextRequest, context:{params:Promise<{path:string[]}>}) {
  const {path}=await context.params;
  if(path.some(p=>p==='.' || p==='..' || p.includes('/') || p.includes('\\'))) return new NextResponse('Invalid path',{status:400});
  if(!['GET','HEAD'].includes(request.method)) {
    const origin=request.headers.get('origin');
    const configured=process.env.APP_ORIGIN;
    if(!origin || origin!==(configured || request.nextUrl.origin)) return NextResponse.json({detail:'Invalid request origin'},{status:403});
  }
  const jar=await cookies();
  if(path.join('/')==='auth/logout') {
    const response=NextResponse.json({status:'logged_out'}); response.cookies.delete('sg_session'); return response;
  }
  const headers=new Headers();
  const type=request.headers.get('content-type'); if(type) headers.set('content-type',type);
  const token=jar.get('sg_session')?.value; if(token) headers.set('authorization',`Bearer ${token}`);
  try {
    const options:RequestInit & {duplex?:string}={method:request.method,headers,cache:'no-store',redirect:'error'};
    if(!['GET','HEAD'].includes(request.method)) {options.body=request.body; options.duplex='half';}
    const upstream=await fetch(`${backend}/${path.map(encodeURIComponent).join('/')}${request.nextUrl.search}`,options);
    if(path.join('/')==='auth/login' && upstream.ok) {
      const data=await upstream.json();
      const response=NextResponse.json({role:data.role});
      response.cookies.set('sg_session',data.access_token,{httpOnly:true,sameSite:'strict',secure:process.env.SECURE_COOKIE==='true',maxAge:3600,path:'/'});
      return response;
    }
    const outputHeaders=new Headers({'Cache-Control':'no-store'});
    for(const name of ['content-type','content-disposition']) {const value=upstream.headers.get(name);if(value)outputHeaders.set(name,value);}
    return new NextResponse(upstream.body,{status:upstream.status,headers:outputHeaders});
  } catch {return NextResponse.json({detail:'Backend unavailable'},{status:502});}
}
export {proxy as GET,proxy as POST,proxy as PUT,proxy as PATCH,proxy as DELETE};
