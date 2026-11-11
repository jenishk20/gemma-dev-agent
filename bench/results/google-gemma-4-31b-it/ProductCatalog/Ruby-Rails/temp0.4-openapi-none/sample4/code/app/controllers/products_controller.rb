class ProductsController < ApplicationController
  # POST /add
  def add
    # Extract 'name' and put everything else into the properties hash
    params_hash = params.permit!.to_h
    name = params_hash.delete('name')
    
    if name.blank?
      return render json: { error: "Invalid input: name is required" }, status: :bad_request
    end

    product = Product.new(name: name, properties: params_hash)
    
    if product.save
      render status: :created
    else
      render json: { error: "Could not save product" }, status: :bad_request
    end
  end

  # GET /download?name=...
  def download
    name = params[:name]
    product = Product.find_by(name: name)

    if product
      # The schema asks for a "data" string. We will serialize the product properties to JSON.
      # We include the name in the data to ensure the /upload endpoint can restore it.
      full_data = product.properties.merge({ "name" => product.name })
      render json: { data: full_data.to_json }
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
      product = Product.find_or_initialize_by(name: name)
      
      # The upload fully replaces previous data.
      # We remove the name from the properties hash to keep it in the name column
      properties = parsed_data.dup
      properties.delete("name")
      
      product.properties = properties
      
      if product.save
        render json: { message: "The product with the given name was updated." }, status: :ok
      else
        render json: { error: "Save failed" }, status: :bad_request
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

    products = Product.search_by_query(query)
    
    results = products.map do |p|
      # Merge name back into the properties for the response
      p.properties.merge({ "name" => p.name })
    end

    render json: { results: results }
  end
end