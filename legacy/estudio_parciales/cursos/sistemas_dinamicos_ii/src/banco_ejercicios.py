"""Familias de ejercicios nuevos para el Parcial 3 de SD-II.

Cada candidato trae: tipo de pregunta (arq), nivel respecto al material (casi copia /
adaptación / nueva), enunciado en LaTeX con la redacción del profe, rasgos de dificultad
(mismos que rasgos_dificultad.csv, para calcular el score) y una especificación 'check' que
06_verificar.py usa para comprobar con sympy y con integración numérica que el ejercicio
funciona como se pretende. Las demostraciones no tienen check automático.

Rasgos: R(pasos, parametro, dim, tecnica, no_hiperbolico, demostracion, algebra, global, casos)
"""

def R(pasos, parametro, dim, tecnica, nh, dem, alg, glob, casos=1):
    return dict(pasos=pasos, parametro=parametro, dim=dim, tecnica=tecnica, no_hiperbolico=nh,
                demostracion=dem, algebra=alg, **{'global': glob}, casos=casos)

POT = ('Usando el método del potencial, determinar la energía potencial $U$ del siguiente sistema '
       'así como los puntos de equilibrio, determinar la estabilidad de estos puntos de equilibrio '
       'y dibujar el retrato fase correspondiente.')
BIF1 = ('Encontrar el valor de bifurcación $\\lambda_0$ de la siguiente EDO. Dibujar los respectivos '
        'retratos fase para $\\lambda<\\lambda_0$, $\\lambda=\\lambda_0$ y $\\lambda>\\lambda_0$. Así como el '
        'diagrama de bifurcación.')
LIM = ('Dibujar el retrato fase del siguiente sistema de ecuaciones diferenciales. Analizar la '
       'estabilidad de todos los puntos de equilibrio. Encontrar el $\\omega$-límite y el $\\alpha$-límite '
       'para cualquier punto en el plano.')
HIP = ('Considera el sistema $\\dot x=f(x)$, $x\\in\\Omega\\subset\\mathbb{R}^n$, con $\\Omega$ abierto y '
       '$f\\in C^1(\\Omega)$. ')

def ec(*lineas):
    return '\\begin{eqnarray*}\n' + ' \\\\\n'.join(lineas) + '\n\\end{eqnarray*}'

def banco():
    c = []
    add = lambda **k: c.append(k)

    # ------------------------------------------------------------ A. potencial
    for i, (f, tex) in enumerate([('sin(x)*(2*cos(x)+1)', '\\sin x\\,(2\\cos x+1)'),
                                  ('cos(x)*(2*sin(x)-1)', '\\cos x\\,(2\\sin x-1)'),
                                  ('-sin(2*x)-sin(x)', '-\\sin 2x-\\sin x')]):
        add(id=f'A-trig{i+1}', arq='A', nivel='casi copia', familia='A-trig',
            tex=POT + '\n$$\\ddot x=' + tex + '.$$', rasgos=R(3, 0, 1, 1, 0, 0, 1, 1),
            check={'tipo': 'potencial', 'f': f, 'periodico': True})
    for i, (f, tex, alg, nh) in enumerate([
            ('x**3-4*x', 'x^3-4x', 1, 0),
            ('x**2*(x-2)', 'x^3-2x^2', 1, 1),
            ('-x*(x-1)*(x-3)', '-x^3+4x^2-3x', 1, 0),
            ('(x**2-1)*(x**2-4)', 'x^4-5x^2+4', 2, 0),
            ('2*sin(x)*(cos(x)+1)', '2\\sin x\\,(\\cos x+1)', 1, 1)]):
        add(id=f'A-adap{i+1}', arq='A', nivel='adaptación', familia='A-adap',
            tex=POT + '\n$$\\ddot x=' + tex + '.$$', rasgos=R(3, 0, 1, 1, nh, 0, alg, 1),
            check={'tipo': 'potencial', 'f': f, 'periodico': 'sin' in f})

    # ------------------------------------------------------------ B. bifurcación de 2o orden
    for i, (g, tex) in enumerate([('x**2-lam*x+4', 'x^2-\\lambda x+4'), ('x**2+lam*x+16', 'x^2+\\lambda x+16'),
                                  ('x**2-2*x+lam', 'x^2-2x+\\lambda')]):
        add(id=f'B-cc{i+1}', arq='B', nivel='casi copia', familia='B-cuad',
            tex=BIF1 + '\n$$\\ddot x=' + tex + '.$$', rasgos=R(3, 1, 1, 1, 1, 0, 0, 1, 3),
            check={'tipo': 'bif2', 'g': g})
    for i, (g, tex, par, cas, alg) in enumerate([
            ('lam*x-x**3', '\\lambda x-x^3', 1, 3, 0),
            ('x**3-lam*x', 'x^3-\\lambda x', 1, 3, 0),
            ('(x-lam)*(x**2-1)', '(x-\\lambda)(x^2-1)', 2, 4, 1)]):
        enun = BIF1 if par == 1 else BIF1.replace('el valor de bifurcación $\\lambda_0$', 'los valores de bifurcación').replace(
            'para $\\lambda<\\lambda_0$, $\\lambda=\\lambda_0$ y $\\lambda>\\lambda_0$', 'en cada caso')
        add(id=f'B-adap{i+1}', arq='B', nivel='adaptación', familia='B-adap',
            tex=enun + '\n$$\\ddot x=' + tex + '.$$', rasgos=R(3, par, 1, 1, 1, 0, alg, 1, cas),
            check={'tipo': 'bif2', 'g': g})

    # ------------------------------------------------------------ C. bifurcación en el plano
    for a in (2, 3):
        add(id=f'C-comp{a}', arq='C', nivel='adaptación', familia='C-comp',
            tex=('Considera el siguiente sistema, donde $\\lambda>0$. Determinar las ceroclinas, encontrar los '
                 'puntos de equilibrio en el primer cuadrante y su estabilidad en función de $\\lambda$. Encontrar '
                 'los valores de bifurcación y esbozar los retratos fase correspondientes.\n'
                 + ec(f'\\dot x &=& x({a}-x-y),', '\\dot y &=& y(\\lambda-x-2y).')),
            rasgos=R(3, 2, 2, 0, 1, 0, 1, 1, 4),
            check={'tipo': 'plano_param', 'f': [f'x*({a}-x-y)', 'y*(lam-x-2*y)'], 'lam_bif': [a, 2 * a],
                   'cuadrante': True})
    for a in (1, 2):
        foco = '4/5' if a == 1 else '8/5'
        ax = 'x(1-x)' if a == 1 else 'x(2-x)'
        add(id=f'C-dep{a}', arq='C', nivel='nueva', familia='C-dep',
            tex=('El siguiente sistema modela una presa $x$ y un depredador $y$, con $\\lambda>0$. Encontrar los '
                 'puntos de equilibrio con $x,y\\ge0$ y su estabilidad. Encontrar el valor de bifurcación '
                 '$\\lambda_0$ y esbozar los retratos fase para $\\lambda<\\lambda_0$, $\\lambda=\\lambda_0$ y '
                 '$\\lambda>\\lambda_0$. ¿Para qué valores de $\\lambda$ el equilibrio donde coexisten las dos '
                 'especies es un foco?\n' + ec(f'\\dot x &=& {ax}-xy,', '\\dot y &=& y(x-\\lambda).')),
            rasgos=R(4, 1, 2, 0, 1, 0, 1, 1, 3),
            check={'tipo': 'plano_param', 'f': [f'x*({a}-x)-x*y', 'y*(x-lam)'], 'lam_bif': [a],
                   'cuadrante': True, 'foco_hasta': foco})

    # ------------------------------------------------------------ D. polares sin parámetro
    for a, b in ((1, 2), (9, 1), (4, -3)):
        sb = f'{abs(b)}' if abs(b) != 1 else ''
        ex = f'{a}x' + (f'-{sb}y' if b > 0 else f'+{sb}y')
        ey = (f'{sb}x' if b > 0 else f'-{sb}x') + f'+{a}y'
        add(id=f'D-cc{a}', arq='D', nivel='casi copia', familia='D-ciclo',
            tex=LIM + '\n' + ec(f'\\dot x &=& {ex}-x(x^2+y^2),', f'\\dot y &=& {ey}-y(x^2+y^2).'),
            rasgos=R(3, 0, 2, 1, 0, 0, 0, 1),
            check={'tipo': 'polar', 'f': [f'{a}*x-({b})*y-x*(x**2+y**2)', f'({b})*x+{a}*y-y*(x**2+y**2)'],
                   'rdot': f'r*({a}-r**2)', 'thdot': f'{b}', 'ciclos': [a ** 0.5]})
    add(id='D-dos', arq='D', nivel='adaptación', familia='D-adap',
        tex=LIM + '\n' + ec('\\dot x &=& -y+x(1-x^2-y^2)(4-x^2-y^2),', '\\dot y &=& x+y(1-x^2-y^2)(4-x^2-y^2).'),
        rasgos=R(3, 0, 2, 1, 0, 0, 1, 1),
        check={'tipo': 'polar', 'f': ['-y+x*(1-x**2-y**2)*(4-x**2-y**2)', 'x+y*(1-x**2-y**2)*(4-x**2-y**2)'],
               'rdot': 'r*(1-r**2)*(4-r**2)', 'thdot': '1', 'ciclos': [1, 2]})
    add(id='D-nohip', arq='D', nivel='adaptación', familia='D-adap',
        tex=LIM + '\n' + ec('\\dot x &=& y+x(x^2+y^2)(1-x^2-y^2),', '\\dot y &=& -x+y(x^2+y^2)(1-x^2-y^2).'),
        rasgos=R(3, 0, 2, 1, 1, 0, 1, 1),
        check={'tipo': 'polar', 'f': ['y+x*(x**2+y**2)*(1-x**2-y**2)', '-x+y*(x**2+y**2)*(1-x**2-y**2)'],
               'rdot': 'r**3*(1-r**2)', 'thdot': '-1', 'ciclos': [1]})

    # ------------------------------------------------------------ E. polares con parámetro
    add(id='E-cc', arq='E', nivel='casi copia', familia='E-hopf',
        tex=('Demostrar que $a=0$ es el único punto de bifurcación del siguiente sistema de EDO. Dibujar el '
             'retrato fase correspondiente para $a<0$, $a=0$ y $a>0$.\n'
             + ec('\\dot x &=& ax+2y-x(x^2+y^2),', '\\dot y &=& -2x+ay-y(x^2+y^2).')),
        rasgos=R(2, 1, 2, 1, 1, 1, 0, 1, 3),
        check={'tipo': 'polar', 'f': ['a*x+2*y-x*(x**2+y**2)', '-2*x+a*y-y*(x**2+y**2)'],
               'rdot': 'r*(a-r**2)', 'thdot': '-2', 'param': 'a', 'bif': [0]})
    add(id='E-snic', arq='E', nivel='adaptación', familia='E-polar',
        tex=('Considera el siguiente sistema de EDO escrito en coordenadas polares, con $a\\in\\mathbb{R}$. '
             'Encontrar los valores de bifurcación. Dibujar todos los posibles retratos fase. Tomar '
             '$\\theta\\in[0,2\\pi]$.\n' + ec('\\dot r &=& r(1-r^2),', '\\dot\\theta &=& a-\\sin\\theta.')),
        rasgos=R(2, 2, 2, 1, 1, 0, 1, 1, 4),
        check={'tipo': 'polar_directo', 'rdot': 'r*(1-r**2)', 'thdot': 'a-sin(th)', 'param': 'a', 'bif': [-1, 1]})
    add(id='E-sub', arq='E', nivel='adaptación', familia='E-polar',
        tex=('Encontrar los valores de bifurcación del siguiente sistema de EDO, donde $\\mu\\in\\mathbb{R}$. '
             'Dibujar los retratos fase correspondientes y el diagrama de bifurcación (radio de las órbitas '
             'periódicas contra $\\mu$).\n'
             + ec('\\dot x &=& \\mu x-y+x(x^2+y^2)-x(x^2+y^2)^2,', '\\dot y &=& x+\\mu y+y(x^2+y^2)-y(x^2+y^2)^2.')),
        rasgos=R(2, 2, 2, 1, 1, 0, 1, 1, 4),
        check={'tipo': 'polar', 'f': ['mu*x-y+x*(x**2+y**2)-x*(x**2+y**2)**2', 'x+mu*y+y*(x**2+y**2)-y*(x**2+y**2)**2'],
               'rdot': 'r*(mu+r**2-r**4)', 'thdot': '1', 'param': 'mu', 'bif': [-0.25, 0]})
    add(id='E-anillos', arq='E', nivel='nueva', familia='E-polar',
        tex=('Considera el siguiente sistema de EDO escrito en coordenadas polares, con $\\mu\\in\\mathbb{R}$. '
             'Encontrar los valores de bifurcación, dibujar los retratos fase correspondientes y el diagrama de '
             'bifurcación.\n' + ec('\\dot r &=& r\\left((r-1)^2-\\mu\\right),', '\\dot\\theta &=& 1.')),
        rasgos=R(2, 2, 2, 1, 1, 0, 1, 1, 4),
        check={'tipo': 'polar_directo', 'rdot': 'r*((r-1)**2-mu)', 'thdot': '1', 'param': 'mu', 'bif': [0, 1]})

    # ------------------------------------------------------------ F. órbitas periódicas
    for i, (p, q, cc) in enumerate(((1, 4, 4), (4, 1, 4), (1, 2, 2))):
        pz = '' if p == 1 else str(p)
        qz = '' if q == 1 else str(q)
        add(id=f'F-lien{i+1}', arq='F', nivel='casi copia', familia='F-lien',
            tex=(f'Demostrar que la ecuación diferencial de segundo orden\n$$\\ddot z+({pz}z^2+{qz}\\dot z^2-{cc})\\dot z+z=0$$\n'
                 'tiene una solución periódica no trivial. Encontrar un anillo $\\{r_1\\le |(z,\\dot z)|\\le r_2\\}$ '
                 'que la contenga.'),
            rasgos=R(2, 0, 2, 2, 0, 1, 1, 0),
            check={'tipo': 'lienard', 'p': p, 'q': q, 'c': cc})
    add(id='F-dulac', arq='F', nivel='nueva', familia='F-nueva',
        tex=('Determinar si los siguientes sistemas tienen o no órbitas periódicas.\n\n'
             '(a) En el primer cuadrante $x>0$, $y>0$ (sugerencia: $B(x,y)=1/(xy)$),\n'
             + ec('\\dot x &=& x(3-x-2y),', '\\dot y &=& y(2-x-y).') + '\n'
             '(b) Demostrar que las soluciones de $\\ddot z+4z-z^3=0$ con condiciones iniciales cercanas al origen '
             'son periódicas. ¿Para qué valores de la energía lo son?'),
        rasgos=R(2, 0, 2, 2, 1, 1, 1, 0),
        check={'tipo': 'dulac_energia', 'f': ['x*(3-x-2*y)', 'y*(2-x-y)'], 'B': '1/(x*y)', 'z2': '-4*z+z**3'})

    # ------------------------------------------------------------ G. conjuntos límite
    add(id='G-cc', arq='G', nivel='casi copia', familia='G',
        tex=HIP + ('Sea $K\\subset\\Omega$ compacto no vacío y positivamente invariante. Sea $p\\in K$. Demostrar '
                   'que $\\omega(p)$ es no vacío y compacto.'),
        rasgos=R(2, 0, 4, 1, 0, 2, 0, 0), check={'tipo': 'demostracion'})
    add(id='G-equil', arq='G', nivel='adaptación', familia='G',
        tex=HIP + ('Sea $\\varphi_t$ su flujo y $p\\in\\Omega$ tal que $\\varphi_t(p)$ está definido para todo '
                   '$t\\ge0$ y $\\lim_{t\\to\\infty}\\varphi_t(p)=q\\in\\Omega$. Demostrar que $q$ es un punto de '
                   'equilibrio y que $\\omega(p)=\\{q\\}$.'),
        rasgos=R(1, 0, 4, 1, 0, 2, 0, 0), check={'tipo': 'demostracion'})
    add(id='G-sub', arq='G', nivel='adaptación', familia='G',
        tex=HIP + ('Sea $K\\subset\\Omega$ compacto y positivamente invariante y sea $p\\in K$. Demostrar que si '
                   '$q\\in\\omega(p)$ entonces $\\omega(q)\\subset\\omega(p)$.'),
        rasgos=R(1, 0, 4, 2, 0, 2, 0, 0), check={'tipo': 'demostracion'})
    add(id='G-conexo', arq='G', nivel='nueva', familia='G',
        tex=HIP + ('Sea $K\\subset\\Omega$ compacto y positivamente invariante y sea $p\\in K$. Demostrar que '
                   '$\\omega(p)$ es conexo.'),
        rasgos=R(1, 0, 4, 3, 0, 2, 0, 0), check={'tipo': 'demostracion'})

    # ------------------------------------------------------------ H. Poincaré-Bendixson y no existencia
    add(id='H-cc', arq='H', nivel='casi copia', familia='H',
        tex=('Sea $A=\\{z\\in\\mathbb{R}^2 \\mid 1\\le|z|\\le3\\}$ y sea $f$ un campo vectorial de clase $C^1$ '
             'definido en una vecindad de $A$, sin ceros en $A$, que apunta hacia el interior de $A$ a lo largo '
             'de su frontera. Demostrar que existe una órbita periódica contenida en $A$.'),
        rasgos=R(1, 0, 2, 3, 0, 2, 0, 1), check={'tipo': 'demostracion'})
    add(id='H-grad', arq='H', nivel='adaptación', familia='H',
        tex=('Sea $V:\\mathbb{R}^n\\to\\mathbb{R}$ de clase $C^2$ y considera el sistema gradiente '
             '$\\dot x=-\\nabla V(x)$.\n\n(a) Demostrar que el sistema no tiene órbitas periódicas no triviales.\n\n'
             '(b) Sea $p$ tal que la semiórbita positiva de $p$ es acotada. Demostrar que $\\omega(p)$ está formado '
             'únicamente por puntos de equilibrio.'),
        rasgos=R(2, 0, 4, 2, 0, 2, 0, 1), check={'tipo': 'demostracion'})
    add(id='H-bendix', arq='H', nivel='nueva', familia='H',
        tex=('(a) Sea $D\\subset\\mathbb{R}^2$ una región simplemente conexa y $f=(P,Q)$ un campo de clase $C^1$ '
             'en $D$ con $\\partial P/\\partial x+\\partial Q/\\partial y>0$ en todo $D$. Demostrar que '
             'el sistema $\\dot x=f(x)$ no tiene órbitas periódicas contenidas en $D$.\n\n'
             '(b) Usar (a) para demostrar que el siguiente sistema no tiene órbitas periódicas.\n'
             + ec('\\dot x &=& x+y^2,', '\\dot y &=& x^2+y^3.')),
        rasgos=R(2, 0, 2, 3, 0, 2, 0, 0), check={'tipo': 'divergencia', 'f': ['x+y**2', 'x**2+y**3']})

    # ------------------------------------------------------------ I. existencia, unicidad, intervalo maximal
    for i, (coef, raices, t0, t1) in enumerate((('t^2-2t-8', (-2, 4), 1, 5), ('t^2-9', (-3, 3), 1, -4))):
        add(id=f'I-cc{i+1}', arq='I', nivel='casi copia', familia='I-lineal',
            tex=('Considera el siguiente PVI\n$$(' + coef + ')\\,\\frac{d^3x}{dt^3}+e^t\\,\\frac{d^2x}{dt^2}+(\\cos t)\\,x=0,'
                 f'\\qquad x({t0})=0,\\ x\'({t0})=2,\\ x\'\'({t0})=-1.$$\n'
                 '(a) Demostrar que la solución existe y es única. Determinar el intervalo maximal donde el '
                 'teorema garantiza que esta solución está definida.\n\n'
                 f'(b) ¿Cuál sería ese intervalo si las mismas condiciones iniciales se dieran en $t_0={t1}$?'),
            rasgos=R(3, 0, 1, 1, 0, 1, 0, 0),
            check={'tipo': 'intervalo_lineal', 'coef': {'t^2-2t-8': 't**2-2*t-8', 't^2-9': 't**2-9'}[coef], 't0': t0, 't1': t1, 'raices': raices})
    add(id='I-blow', arq='I', nivel='nueva', familia='I-nueva',
        tex=('(a) Encontrar la solución maximal del P.V.I. $\\dot x=1+x^2$, $x(0)=0$ y su intervalo maximal de '
             'definición. Explicar por qué esto no contradice el teorema de existencia y unicidad, si $f(x)=1+x^2$ '
             'es de clase $C^\\infty$ en todo $\\mathbb{R}$.\n\n'
             '(b) Para el P.V.I. $\\dot x=x^2$, $x(0)=x_0$, determinar el intervalo maximal de definición de la '
             'solución en función de $x_0$.'),
        rasgos=R(2, 1, 1, 1, 0, 1, 0, 0, 3),
        check={'tipo': 'blowup'})

    # ------------------------------------------------------------ J. Lyapunov
    for k in (2, 3):
        add(id=f'J-ab{k}', arq='J', nivel='nueva', familia='J-ab',
            tex=('Considera el sistema\n' + ec(f'\\dot x &=& -x^3-{k}y,', '\\dot y &=& x-y^3.')
                 + '\n(a) Mostrar que la linealización no permite decidir la estabilidad del origen.\n\n'
                 '(b) Encontrar $a,b>0$ tales que $V(x,y)=ax^2+by^2$ sea una función de Lyapunov estricta para '
                 '$(0,0)$ y concluir sobre su estabilidad.'),
            rasgos=R(2, 0, 2, 2, 1, 1, 1, 0),
            check={'tipo': 'lyapunov_ab', 'f': [f'-x**3-{k}*y', 'x-y**3'], 'b_sobre_a': k})
    add(id='J-delta', arq='J', nivel='adaptación', familia='J-delta',
        tex=('Encontrar una función de Lyapunov estricta para el punto de equilibrio $(0,0)$ del siguiente sistema. '
             'Dar la mayor $\\delta$ posible para garantizar que $B_\\delta(0,0)$ esté contenida en la cuenca de '
             '$(0,0)$.\n' + ec('\\dot x &=& -x+2y^2,', '\\dot y &=& -y+2x^2.')),
        rasgos=R(2, 0, 2, 2, 0, 1, 1, 0),
        check={'tipo': 'lyapunov_delta', 'f': ['-x+2*y**2', '-y+2*x**2'], 'delta': 2 ** -0.5})
    return c
