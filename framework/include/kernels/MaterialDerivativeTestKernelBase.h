/****************************************************************/
/*               DO NOT MODIFY THIS HEADER                      */
/* MOOSE - Multiphysics Object Oriented Simulation Environment  */
/*                                                              */
/*           (c) 2010 Battelle Energy Alliance, LLC             */
/*                   ALL RIGHTS RESERVED                        */
/*                                                              */
/*          Prepared by Battelle Energy Alliance, LLC           */
/*            Under Contract No. DE-AC07-05ID14517              */
/*            With the U. S. Department of Energy               */
/*                                                              */
/*            See COPYRIGHT for full restrictions               */
/****************************************************************/

#ifndef MATERIALDERIVATIVETESTKERNELBASE_H
#define MATERIALDERIVATIVETESTKERNELBASE_H

#include "Kernel.h"
#include "JvarMapInterface.h"
#include "DerivativeMaterialInterface.h"

/**
 * This kernel is used for testing derivatives of a material property.
 */
template <typename T>
class MaterialDerivativeTestKernelBase
    : public DerivativeMaterialInterface<JvarMapKernelInterface<Kernel>>
{
public:
  MaterialDerivativeTestKernelBase(const InputParameters & parameters);

  static InputParameters validParams();

protected:
  /// number of nonlinear variables
  const unsigned int _n_vars;

  /// material property for which to test derivatives
  const MaterialProperty<T> & _p;

  /// material properties for the off-diagonal derivatives of the tested property
  std::vector<const MaterialProperty<T> *> _p_off_diag_derivatives;

  /// material property for the diagonal derivative of the tested property
  const MaterialProperty<T> & _p_diag_derivative;
};

template <typename T>
MaterialDerivativeTestKernelBase<T>::MaterialDerivativeTestKernelBase(
    const InputParameters & parameters)
  : DerivativeMaterialInterface<JvarMapKernelInterface<Kernel>>(parameters),
    _n_vars(_coupled_moose_vars.size()),
    _p(this->template getMaterialProperty<T>("material_property")),
    _p_off_diag_derivatives(_n_vars),
    _p_diag_derivative(
        this->template getMaterialPropertyDerivative<T>("material_property", _var.name()))
{
  for (unsigned int m = 0; m < _n_vars; ++m)
    _p_off_diag_derivatives[m] = &this->template getMaterialPropertyDerivative<T>(
        "material_property", _coupled_moose_vars[m]->name());
}

template <typename T>
InputParameters
MaterialDerivativeTestKernelBase<T>::validParams()
{
  InputParameters params = ::validParams<Kernel>();
  params.addClassDescription("Class used for testing derivatives of a material property.");
  params.addRequiredParam<MaterialPropertyName>(
      "material_property", "Name of material property for which derivatives are to be tested.");
  params.addRequiredCoupledVar("args", "List of variables the material property depends on");

  return params;
}

#endif // MATERIALDERIVATIVETESTKERNELBASE_H