const indexName = 'comfy_outputs_v001'

const state = $state ( {  
        
        searchParameters : {
        indexName : indexName,
        q : "a ",
        filters : [],
        facets :  ["*"],
        page : 1,      	
        } 
} ) 


export const global = {  

        setSearchParameters (p)  {
                state.searchParameters = { ...p}
                console.log("state:global", p , state)
        }, 

        getSearchParameters() {
                return state.searchParameters
        }

}