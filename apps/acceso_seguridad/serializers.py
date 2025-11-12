from rest_framework import serializers
from typing import Optional, Dict, Any
from .models import Usuario, Bitacora, Aviso 

class UsuarioReadSerializer(serializers.ModelSerializer):

    # cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'nombre', 'apellido', 'telefono', 'is_active', 'last_login', 'is_superuser', 'rol']

class UsuarioWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'password', 'nombre', 'apellido', 'telefono', 'is_active', 'rol']

    def to_internal_value(self, data):
        if self.instance and 'password' not in data:
            self.fields['password'].required = False
        return super().to_internal_value(data)
        if not self.instance and 'password' not in data:
             self.fields['password'].required = True
        return super().to_internal_value(data)

    def create(self, validated_data):
        password = validated_data.pop('password')

        try:
            user = Usuario(**validated_data)
            user.set_password(password)
            user.save()
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'password', 'nombre', 'apellido', 'rol']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user

class PerfilSerializer(serializers.ModelSerializer):
    usuario_info = serializers.SerializerMethodField() 
    class Meta:
        model = Usuario
        fields = ['id', 'correo', 'nombre', 'apellido', 'is_superuser', 'usuario_info']

    def get_usuario_info(self, obj) -> Optional[Dict[str, Any]]:
        """Return related cliente info for this Usuario or None.

        drf-spectacular needs a return type to infer the schema for
        SerializerMethodField; adding Optional[Dict[str, Any]] fixes the
        "unable to resolve type hint" warning.
        """
        cliente = getattr(obj, 'cliente', None)
        if cliente:
            return {
                'id': getattr(cliente, 'id', None),
                'nombre': getattr(cliente, 'nombre', ''),
                'apellidos': getattr(cliente, 'apellidos', ''),
            }
        return None

class RecuperarPasswordSerializer(serializers.Serializer):
    correo = serializers.EmailField()

class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField()
    password_nueva = serializers.CharField(min_length=4)


class LoginSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class BitacoraSerializer(serializers.ModelSerializer):
    usuario_correo = serializers.CharField(source='usuario.correo', read_only=True)

    class Meta:
        model = Bitacora
        fields = ['id', 'usuario', 'usuario_correo', 'accion', 'descripcion', 'ip', 'fecha']
        read_only_fields = ['fecha']

class SolicitarRecuperacionSerializer(serializers.Serializer):
    correo = serializers.EmailField()

class ConfirmarRecuperacionSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=100)
    nueva_password = serializers.CharField(min_length=6, max_length=128)
    confirmar_password = serializers.CharField(max_length=128)
    
    def validate(self, attrs):
        if attrs['nueva_password'] != attrs['confirmar_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs

class AvisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aviso
        fields = [
            'id', 
            'asunto',
            'mensaje', 
            'tipo',
            'estado',
            'prioridad',
            'fecha_push', 
            'hora_push',
            'imagen_url',
            'link_accion',
            'urgente'
        ]
        extra_kwargs = {
            'imagen_url': {'required': False, 'allow_blank': True, 'allow_null': True},
            'link_accion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'fecha_push': {'required': False, 'allow_null': True},
            'hora_push': {'required': False, 'allow_null': True},
            'tipo': {'required': False},
            'prioridad': {'required': False},
        }
    
    def to_representation(self, instance):
        """Convertir asunto a titulo para el frontend"""
        data = super().to_representation(instance)
        data['titulo'] = data.get('asunto', '')
        return data
    
    def create(self, validated_data):
        """Manejar el campo titulo del frontend"""
        # Si no viene asunto pero sí titulo en los datos iniciales
        if 'asunto' not in validated_data or not validated_data.get('asunto'):
            if 'titulo' in self.initial_data:
                validated_data['asunto'] = self.initial_data['titulo']
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Manejar el campo titulo del frontend"""
        # Si viene titulo en los datos iniciales, usarlo como asunto
        if 'titulo' in self.initial_data and not validated_data.get('asunto'):
            validated_data['asunto'] = self.initial_data['titulo']
        
        return super().update(instance, validated_data)