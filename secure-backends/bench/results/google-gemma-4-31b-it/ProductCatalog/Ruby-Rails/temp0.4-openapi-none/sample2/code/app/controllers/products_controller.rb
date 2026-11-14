class ProductsController < ApplicationController
  # POST /add
  def add
    # Separate 'name' from the rest of the unstructured properties
    params_hash = params.permit!.to_h
    name = params_hash.delete('name')

    if name.blank?
      return render json: { error: "Invalid input: name is required" }, status: :bad_request
    end

    product = Product.new(name: name, properties: params_hash)
    
    if product.save
      render status: :created
    else
      render json: { error: product.errors.full_messages }, status: :bad_request
    end
  end

  # GET /download?name=...
  def download
    name = params[:name]
    product = Product.find_by(name: name)

    if product
      # The spec asks for the data as a string (the "data entry")
      # We serialize the full object (name + properties) to JSON string
      render json: { data: product.to_catalog_hash.to_json }
    else
      render json: { error: "Product not found" }, status: :bad_request
    end
  end

  # POST /upload
  def upload
    name = params[:name]
    data_string = params[:data]

    if name.blank? || data_string.blank?
      return render json: { error: "Invalid upload query" }, status: :bad_request
    end

    begin
      parsed_data = JSON.parse(data_string)
      # The upload fully replaces previous data. 
      # We ensure the name in the data matches or we prioritize the 'name' param.
      product = Product.find_or_initialize_by(name: name)
      
      # Remove name from properties to avoid duplication in the JSON column
      properties = parsed_data.dup
      properties.delete('name')
      
      product.name = name
      product.properties = properties
      
      if product.save
        render json: { message: "The product with the given name was updated." }, status: :ok
      else
        render json: { error: product.errors.full_messages }, status: :bad_request
      end
    rescue JSON::ParserError
      render json: { error: "Invalid JSON data" }, status: :bad_request
    end
  end

  # GET /search?query=...
  def search
    query = params[:query]
    if query.blank?
      return render json: { error: "Invalid search query" }, status: :bad_request
    end

    # Search in name OR within the JSON properties column
    # SQLite supports 'LIKE' on the text representation of the JSON column
    products = Product.where("name LIKE ?", "%#{query}%")
                      .where("properties LIKE ?", "%#{query}%")
                      .or(Product.where("name LIKE ?", "%#{query}%")) # Simplified for SQLite
    
    # To be more precise with SQLite's JSON, we filter the results
    results = Product.all.select do |p| 
      p.name.include?(query) || (p.properties && p.properties.values.any? { |v| v.to_s.include?(query) })
    end

    render json: { results: results.map(&:to_catalog_hash) }
  end
end