% NKM Linearizzato (16.04.2024)
% Giovanni Pio Cirillo

% PREAMBOLO
% var endogene (lettera minuscola) -> sono 10
var lambda c w l r pi mc a y is;

% var esogene
varexo eps ms;

% parametri (lettera maiuscola) -> sono 7
parameters GAMMA OMEGA BETA KAPPA PHIP RHOA RHOM;
GAMMA = 1;
OMEGA = 0.75;
BETA = 0.99;
KAPPA = (1-OMEGA)*(1-(BETA*OMEGA))/(OMEGA);
PHIP = 1.5;
RHOA = 0.7;
RHOM = 0.5;

% MODELLO
model(linear);

%famiglie
lambda = -c;
w = (GAMMA*l) - lambda;
lambda = lambda(+1) + r - pi(+1);

%imprese
w = mc + a;
y = a + l;
y = c;
a = RHOA*a(-1) + eps;

%banca centrale
r = (PHIP*pi) + is;
is = (RHOM*is(-1)) + ms;

%stato economia (inflazione)
pi = (KAPPA*mc) + (BETA*pi(+1));

end;

steady;
check;

% SHOCK ESOGENO
shocks;
var eps = 1;
var ms = 1;
end;

stoch_simul(irf=40);
